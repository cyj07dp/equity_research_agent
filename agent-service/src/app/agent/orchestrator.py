import logging
from uuid import UUID

from app.agent.agent_planner import AgentPlanner
from app.agent.reasoning_engine import ReasoningEngine
from app.agent.replanner import ConditionalReplanner
from app.agent.reflection_validator import ReflectionValidator
from app.agent.report_writer import ReportWriter
from app.agent.plan_validator import PlanValidator
from app.agent.tool_router import ToolRouter
from app.llm import create_llm_client_from_env
from app.schemas import (
    AgentRunResult,
    AnalystReasoning,
    ConversationMessage,
    DataSufficiencyResult,
    EvidenceAssessment,
    EvidenceReasoningResult,
    PlanningDecision,
    QueryUnderstanding,
    ReflectionResult,
    ReplanningDecision,
    ReportInstructions,
    ResearchReport,
    ResearchPlan,
    ReportSection,
    ResearchTaskType,
    ToolCallResult,
    EvidenceItem,
    UserPreferences,
)
from app.tools.registry import ToolRegistry

logger = logging.getLogger("uvicorn.error")


class ResearchAgentOrchestrator:
    def __init__(self) -> None:
        llm_client = create_llm_client_from_env()
        tool_registry = ToolRegistry(llm_client=llm_client)

        self.agent_planner = AgentPlanner(llm_client=llm_client)
        self.plan_validator = PlanValidator()
        self.tool_registry = tool_registry
        self.tool_router = ToolRouter(tools=tool_registry.get_tools())
        self.replanner = ConditionalReplanner(llm_client=llm_client)
        self.reasoning_engine = ReasoningEngine(llm_client=llm_client)
        self.report_writer = ReportWriter(llm_client=llm_client)
        self.reflection_validator = ReflectionValidator(llm_client=llm_client)

    def run(
        self,
        run_id: UUID,
        query: str,
        locale: str = "zh-CN",
        conversation_messages: list[ConversationMessage] | None = None,
        user_preferences: UserPreferences | None = None,
    ) -> AgentRunResult:
        effective_query = _effective_query(
            query=query,
            conversation_messages=conversation_messages or [],
            user_preferences=user_preferences,
        )
        conversation_context = _conversation_context(
            conversation_messages=conversation_messages or [],
            user_preferences=user_preferences,
        )
        logger.info("Agent run started run_id=%s query_length=%s locale=%s", run_id, len(query), locale)
        runtime_warnings: list[str] = []
        tool_capabilities = self.tool_registry.capabilities()
        logger.info("Agent stage=agent_planning run_id=%s", run_id)
        agent_plan = self.agent_planner.plan(
            query=effective_query,
            conversation_context=conversation_context,
            user_preferences=(user_preferences or UserPreferences()).model_dump(by_alias=True),
            tool_capabilities=tool_capabilities,
        )
        planning_decision = agent_plan.to_planning_decision()
        understanding = _understanding_from_agent_plan(agent_plan)
        logger.info(
            "Agent stage=agent_planning decision run_id=%s answerability=%s needs_tools=%s allowed_tool_count=%s",
            run_id,
            planning_decision.answerability,
            planning_decision.needs_tools,
            len(planning_decision.allowed_tools),
        )
        if _should_wait_for_clarification(planning_decision):
            logger.info("Agent stage=clarification_short_circuit run_id=%s", run_id)
            return _clarification_result(
                run_id=run_id,
                query=query,
                locale=locale,
                understanding=understanding,
                planning_decision=planning_decision,
            )

        plan = ResearchPlan(objective=planning_decision.objective, steps=planning_decision.steps)
        plan = self.plan_validator.validate(
            plan=plan,
            planning_decision=agent_plan,
        )
        logger.info("Agent stage=agent_planning complete run_id=%s step_count=%s", run_id, len(plan.steps))
        logger.info("Agent stage=tool_router run_id=%s", run_id)
        tool_calls, evidence = self.tool_router.execute(
            plan=plan,
            context={"query": effective_query, "understanding": understanding},
        )
        logger.info(
            "Agent stage=tool_router complete run_id=%s tool_call_count=%s evidence_count=%s",
            run_id,
            len(tool_calls),
            len(evidence),
        )
        if tool_calls and not evidence:
            warning = (
                "工具已执行但未获得可用于支撑回答的 evidence，"
                "本轮跳过后续高成本 LLM 分析并返回降级报告。"
            )
            runtime_warnings.append(warning)
            logger.warning(
                "Agent degraded run_id=%s reason=no_evidence_after_tools tool_call_count=%s",
                run_id,
                len(tool_calls),
            )
            return _no_evidence_degraded_result(
                run_id=run_id,
                query=query,
                locale=locale,
                understanding=understanding,
                planning_decision=planning_decision,
                plan=plan,
                tool_calls=tool_calls,
                runtime_warnings=runtime_warnings,
            )
        replanning_decision = None
        if _should_replan(plan=plan, tool_calls=tool_calls, evidence=evidence):
            logger.info("Agent stage=conditional_replanning run_id=%s", run_id)
            replanning_decision = self.replanner.replan(
                query=effective_query,
                understanding=understanding,
                planning_decision=planning_decision,
                tool_calls=tool_calls,
                evidence=evidence,
                tool_capabilities=tool_capabilities,
            )
            logger.info(
                "Agent stage=conditional_replanning complete run_id=%s action=%s",
                run_id,
                replanning_decision.action,
            )
            if replanning_decision.action == "ASK_CLARIFICATION":
                return _clarification_result(
                    run_id=run_id,
                    query=query,
                    locale=locale,
                    understanding=understanding,
                    planning_decision=_planning_decision_with_replanning_questions(
                        planning_decision,
                        replanning_decision,
                    ),
                    replanning_decision=replanning_decision,
                    runtime_warnings=runtime_warnings,
                )
            if replanning_decision.action == "CALL_ADDITIONAL_TOOLS" and replanning_decision.additional_steps:
                additional_plan = ResearchPlan(
                    objective=replanning_decision.rationale,
                    steps=replanning_decision.additional_steps,
                )
                additional_plan = self.plan_validator.validate(
                    plan=additional_plan,
                    planning_decision=agent_plan,
                )
                additional_calls, additional_evidence = self.tool_router.execute(
                    plan=additional_plan,
                    context={"query": effective_query, "understanding": understanding},
                )
                tool_calls.extend(additional_calls)
                evidence.extend(additional_evidence)

        logger.info("Agent stage=evidence_reasoning run_id=%s", run_id)
        evidence_reasoning = self.reasoning_engine.reason(
            query=effective_query,
            understanding=understanding,
            planning_decision=planning_decision,
            tool_calls=tool_calls,
            evidence=evidence,
        )
        data_sufficiency = evidence_reasoning.data_sufficiency
        reasoning = evidence_reasoning.reasoning
        logger.info(
            "Agent stage=evidence_reasoning complete run_id=%s answerability=%s sufficiency_status=%s",
            run_id,
            evidence_reasoning.answerability,
            data_sufficiency.status,
        )
        logger.info("Agent stage=report_drafting run_id=%s", run_id)
        draft_report = self.report_writer.write_from_reasoning(
            query=effective_query,
            planning_decision=planning_decision,
            data_sufficiency=data_sufficiency,
            report_instructions=evidence_reasoning.report_instructions,
            reasoning=reasoning,
            evidence=evidence,
        )
        logger.info("Agent stage=report_drafting complete run_id=%s", run_id)
        logger.info("Agent stage=reflection run_id=%s", run_id)
        reflection = self.reflection_validator.reflect(
            query=effective_query,
            draft_report=draft_report,
            evidence=evidence,
        )
        logger.info("Agent stage=reflection complete run_id=%s passed=%s", run_id, reflection.passed)
        final_report = draft_report
        if not reflection.passed or reflection.revision_instructions:
            logger.info(
                "Agent stage=report_revision run_id=%s unsupported_claim_count=%s missing_data_count=%s",
                run_id,
                len(reflection.unsupported_claims),
                len(reflection.missing_data),
            )
            final_report = self.report_writer.revise_with_reflection(
                query=effective_query,
                draft_report=draft_report,
                reflection=reflection,
                evidence=evidence,
            )
            logger.info("Agent stage=report_revision complete run_id=%s", run_id)

        logger.info("Agent run completed run_id=%s", run_id)
        return AgentRunResult(
            runId=run_id,
            query=query,
            locale=locale,
            runStatus="COMPLETED",
            runtimeWarnings=runtime_warnings,
            clarificationQuestions=planning_decision.clarification_questions,
            understanding=understanding,
            planningDecision=planning_decision,
            plan=plan,
            toolCalls=tool_calls,
            evidence=evidence,
            replanningDecision=replanning_decision,
            dataSufficiency=data_sufficiency,
            evidenceReasoning=evidence_reasoning,
            reasoning=reasoning,
            draftReport=draft_report,
            reflection=reflection,
            finalReport=final_report,
        )


def _effective_query(
    *,
    query: str,
    conversation_messages: list[ConversationMessage],
    user_preferences: UserPreferences | None = None,
) -> str:
    preferences_text = _user_preferences_text(user_preferences)
    if not conversation_messages and not preferences_text:
        return query
    lines = []
    if preferences_text:
        lines.append(preferences_text)
    if conversation_messages:
        lines.append("[会话历史]\n以下是同一投研会话的历史消息，请结合上下文理解用户最新输入。")
    for message in conversation_messages[-12:]:
        role = message.role.upper()
        content = message.content.strip()
        if content:
            lines.append(f"{role}: {content}")
    lines.append(f"[用户最新输入]\n用户最新输入: {query}")
    return "\n".join(lines)


def _conversation_context(
    *,
    conversation_messages: list[ConversationMessage],
    user_preferences: UserPreferences | None,
) -> str:
    lines = []
    preferences_text = _user_preferences_text(user_preferences)
    if preferences_text:
        lines.append(preferences_text)
    if conversation_messages:
        lines.append("[会话历史]")
        for message in conversation_messages[-12:]:
            content = message.content.strip()
            if content:
                lines.append(f"{message.role.upper()}: {content}")
    return "\n".join(lines)


def _understanding_from_agent_plan(agent_plan) -> QueryUnderstanding:
    companies = agent_plan.intent.companies
    task_type = ResearchTaskType.INVESTMENT_THESIS if companies else ResearchTaskType.MARKET_EXPLORATION
    return QueryUnderstanding(
        taskType=task_type,
        intentSummary=agent_plan.intent.summary,
        intentBreakdown=[],
        entities=agent_plan.intent.entities,
        companies=companies,
        timeHorizon="unspecified",
        analysisAspects=agent_plan.evidence_needs,
        comparisonMode=False,
        userDecisionContext=agent_plan.objective or agent_plan.rationale,
        requiresLiveData=agent_plan.intent.needs_live_data,
        outputStyle="research_memo",
        constraints=agent_plan.intent.constraints,
        clarificationQuestions=agent_plan.clarification_questions,
        confidence=0.8,
    )


def _user_preferences_text(user_preferences: UserPreferences | None) -> str:
    if user_preferences is None or not user_preferences.enabled:
        return ""
    lines = ["[用户长期偏好]"]
    _append_preference_line(lines, "默认市场", _market_label(user_preferences.default_market))
    _append_preference_line(lines, "风险偏好", _risk_label(user_preferences.risk_tolerance))
    _append_preference_line(lines, "投资期限", _horizon_label(user_preferences.time_horizon))
    _append_preference_line(lines, "报告风格", _style_label(user_preferences.report_style))
    _append_preference_line(lines, "关注行业", "、".join(user_preferences.preferred_sectors))
    _append_preference_line(lines, "排除行业", "、".join(user_preferences.excluded_sectors))
    _append_preference_line(lines, "常看资产", "、".join(user_preferences.preferred_assets))
    _append_preference_line(lines, "备注", user_preferences.notes)
    lines.extend([
        "",
        "[偏好使用规则]",
        "1. 长期偏好只能作为默认假设和回答约束。",
        "2. 长期偏好不能作为事实证据。",
        "3. 如果与用户最新问题冲突，优先遵循最新问题。",
        "4. 如果偏好不足以判断，不要强行推断用户意图。",
    ])
    return "\n".join(lines)


def _append_preference_line(lines: list[str], label: str, value: str) -> None:
    normalized = value.strip()
    if normalized:
        lines.append(f"{label}：{normalized}")


def _market_label(value: str) -> str:
    return {
        "US": "美股",
        "HK": "港股",
        "CN": "A 股",
    }.get(value, value)


def _risk_label(value: str) -> str:
    return {
        "LOW": "保守",
        "MEDIUM": "平衡",
        "BALANCED": "平衡",
        "HIGH": "进取",
    }.get(value, value)


def _horizon_label(value: str) -> str:
    return {
        "SHORT_TERM": "短期",
        "MEDIUM_TERM": "中期",
        "LONG_TERM": "长期",
    }.get(value, value)


def _style_label(value: str) -> str:
    return {
        "CONCISE": "简洁结论",
        "DETAILED_MEMO": "详细备忘录",
        "BEGINNER_FRIENDLY": "新手友好",
    }.get(value, value)


def _clarification_result(
    *,
    run_id: UUID,
    query: str,
    locale: str,
    understanding: QueryUnderstanding,
    planning_decision: PlanningDecision,
    replanning_decision: ReplanningDecision | None = None,
    runtime_warnings: list[str] | None = None,
) -> AgentRunResult:
    questions = planning_decision.clarification_questions or understanding.clarification_questions or [
        "你想研究的具体公司、股票代码或市场方向是什么？",
    ]
    plan = ResearchPlan(
        objective=planning_decision.rationale or "需要先澄清用户问题中的关键歧义，再继续研究。",
        steps=[],
    )
    return AgentRunResult(
        runId=run_id,
        query=query,
        locale=locale,
        runStatus="NEEDS_CLARIFICATION",
        runtimeWarnings=runtime_warnings or [],
        clarificationQuestions=questions,
        understanding=understanding,
        planningDecision=planning_decision,
        plan=plan,
        toolCalls=[],
        evidence=[],
        replanningDecision=replanning_decision,
        reasoning=None,
        draftReport=None,
        reflection=None,
        finalReport=None,
    )


def _no_evidence_degraded_result(
    *,
    run_id: UUID,
    query: str,
    locale: str,
    understanding: QueryUnderstanding,
    planning_decision: PlanningDecision,
    plan: ResearchPlan,
    tool_calls: list[ToolCallResult],
    runtime_warnings: list[str],
) -> AgentRunResult:
    failed_tools = [
        call.tool_name
        for call in tool_calls
        if call.status.upper() == "FAILED"
    ]
    missing_messages = ["未获得可用于支撑回答的 evidence。"]
    if failed_tools:
        missing_messages.append("失败工具：" + ", ".join(dict.fromkeys(failed_tools)) + "。")
    data_sufficiency = DataSufficiencyResult(
        status="INSUFFICIENT",
        summary="工具已执行，但当前 evidence 不足，不能可靠回答用户问题。",
        expectedEvidence=planning_decision.evidence_needs,
        availableEvidence=[],
        missingEvidence=missing_messages,
        coverageNotes=runtime_warnings,
    )
    reasoning = AnalystReasoning(
        thesis="当前工具未返回可验证 evidence，不能形成可靠投研判断。",
        supportingPoints=[],
        risks=["如果继续基于缺失证据生成结论，可能误导用户。"],
        valuationNotes=[],
        missingData=missing_messages,
        uncertainty="数据源、API 额度、网络或工具输入可能导致本轮没有获得 evidence。",
    )
    evidence_reasoning = EvidenceReasoningResult(
        answerability="INSUFFICIENT",
        evidenceAssessment=EvidenceAssessment(
            summary=data_sufficiency.summary,
            usableEvidence=[],
            missingEvidence=missing_messages,
            failedTools=failed_tools,
            unsupportedQuestions=["当前问题缺少可用 evidence 支撑。"],
        ),
        dataSufficiency=data_sufficiency,
        reasoning=reasoning,
        reportInstructions=ReportInstructions(
            tone="cautious",
            mustSay=[data_sufficiency.summary],
            mustNotSay=["直接给出买入、卖出或持有建议。"],
            revisedSections=[],
        ),
    )
    report = ResearchReport(
        title="证据不足，无法生成可靠投研结论",
        answerSummary="本轮工具执行后没有获得可用 evidence，因此不生成具体投资判断。",
        companySummary="研究对象需要等待可用数据源返回后再分析。",
        questionUnderstanding=f"用户问题：{query}",
        keyFindings=["工具已执行，但没有获得可验证 evidence。"],
        opportunities=[],
        risks=["缺少市场、基本面、新闻或公告 evidence 时，直接下结论风险较高。"],
        evidenceSummary=data_sufficiency.summary,
        uncertainty=reasoning.uncertainty,
        citations=[],
        nonAdvisoryStatement="本报告为 AI Agent 的降级提示，不构成投资建议。",
        sections=[
            ReportSection(title="当前状态", content=data_sufficiency.summary),
            ReportSection(title="为什么不能直接回答", content="；".join(missing_messages)),
            ReportSection(title="建议下一步", content="检查 API 额度、网络、工具配置或换一个更具体的问题后重试。"),
        ],
    )
    reflection = ReflectionResult(
        passed=True,
        unsupportedClaims=[],
        missingData=missing_messages,
        overconfidentStatements=[],
        revisionInstructions=[],
    )
    return AgentRunResult(
        runId=run_id,
        query=query,
        locale=locale,
        runStatus="DEGRADED",
        runtimeWarnings=runtime_warnings,
        clarificationQuestions=planning_decision.clarification_questions,
        understanding=understanding,
        planningDecision=planning_decision,
        plan=plan,
        toolCalls=tool_calls,
        evidence=[],
        replanningDecision=None,
        dataSufficiency=data_sufficiency,
        evidenceReasoning=evidence_reasoning,
        reasoning=reasoning,
        draftReport=report,
        reflection=reflection,
        finalReport=report,
    )


def _should_replan(
    *,
    plan: ResearchPlan,
    tool_calls: list[ToolCallResult],
    evidence: list[EvidenceItem],
) -> bool:
    if not plan.steps:
        return False
    if any(call.status.upper() == "FAILED" for call in tool_calls):
        return True
    return bool(tool_calls) and not evidence


def _should_wait_for_clarification(planning_decision: PlanningDecision) -> bool:
    return False


def _planning_decision_with_replanning_questions(
    planning_decision: PlanningDecision,
    replanning_decision: ReplanningDecision,
) -> PlanningDecision:
    return PlanningDecision(
        answerability="CLARIFICATION_REQUIRED",
        needsTools=False,
        needsClarification=True,
        allowedTools=[],
        evidenceNeeds=[],
        clarificationQuestions=replanning_decision.clarification_questions,
        maxSteps=0,
        rationale=replanning_decision.rationale,
        objective=planning_decision.objective,
        steps=[],
    )
