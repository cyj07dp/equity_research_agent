from app.schemas import AgentPlanDecision, PlanningDecision, QueryUnderstanding, ResearchPlan, ResearchPlanStep

TICKER_ONLY_TOOLS = {
    "market_data",
    "fundamentals",
    "filings_search",
    "sec_company_facts",
    "sec_filing_retriever",
}


class PlanValidator:
    def validate(
        self,
        *,
        plan: ResearchPlan,
        understanding: QueryUnderstanding | None = None,
        planning_decision: AgentPlanDecision | PlanningDecision | None = None,
    ) -> ResearchPlan:
        if planning_decision is None:
            return ResearchPlan(objective=plan.objective, steps=plan.steps[:6])
        if planning_decision.needs_clarification and not planning_decision.needs_tools:
            return ResearchPlan(objective=plan.objective, steps=[])
        allowed_tools = set(planning_decision.allowed_tools)
        max_steps = max(0, min(planning_decision.max_steps, 6))
        valid_steps = [
            step
            for step in plan.steps
            if _step_allowed(
                step=step,
                planning_decision=planning_decision,
                understanding=understanding,
                allowed_tools=allowed_tools,
            )
        ][:max_steps]

        return ResearchPlan(objective=plan.objective, steps=valid_steps)


def _step_allowed(
    *,
    step: ResearchPlanStep,
    planning_decision: AgentPlanDecision | PlanningDecision,
    understanding: QueryUnderstanding | None,
    allowed_tools: set[str],
) -> bool:
    tool_name = step.tool_name or step.tool
    if not tool_name:
        return False
    if allowed_tools and tool_name not in allowed_tools:
        return False
    if tool_name == "web_article_reader":
        return _has_concrete_url(step.tool_input)
    if tool_name in TICKER_ONLY_TOOLS and not _has_ticker(
        step=step,
        planning_decision=planning_decision,
        understanding=understanding,
    ):
        return False
    if tool_name == "news_search" and _is_empty_ticker_news(
        step=step,
        planning_decision=planning_decision,
        understanding=understanding,
    ):
        return False
    return True


def _has_ticker(
    *,
    step: ResearchPlanStep,
    planning_decision: AgentPlanDecision | PlanningDecision,
    understanding: QueryUnderstanding | None,
) -> bool:
    if str(step.tool_input.get("ticker") or "").strip():
        return True
    if isinstance(planning_decision, AgentPlanDecision):
        if any(company.candidates for company in planning_decision.intent.companies):
            return True
        return any(
            entity.best_guess is not None and bool(entity.best_guess.identifier)
            for entity in planning_decision.intent.entities
        )
    if understanding is None:
        return False
    return any(company.candidates for company in understanding.companies)


def _is_empty_ticker_news(
    *,
    step: ResearchPlanStep,
    planning_decision: AgentPlanDecision | PlanningDecision,
    understanding: QueryUnderstanding | None,
) -> bool:
    has_query = bool(str(step.tool_input.get("query") or "").strip())
    has_ticker = _has_ticker(
        step=step,
        planning_decision=planning_decision,
        understanding=understanding,
    )
    return not has_query and not has_ticker


def _has_concrete_url(tool_input: dict) -> bool:
    value = str(tool_input.get("url") or tool_input.get("sourceUrl") or "").strip()
    return value.startswith("http://") or value.startswith("https://")
