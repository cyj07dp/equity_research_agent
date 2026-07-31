from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ResearchTaskType(StrEnum):
    INVESTMENT_THESIS = "INVESTMENT_THESIS"
    COMPANY_OVERVIEW = "COMPANY_OVERVIEW"
    FINANCIAL_HEALTH = "FINANCIAL_HEALTH"
    RECENT_NEWS = "RECENT_NEWS"
    COMPANY_COMPARISON = "COMPANY_COMPARISON"
    MARKET_EXPLORATION = "MARKET_EXPLORATION"
    BEGINNER_GUIDANCE = "BEGINNER_GUIDANCE"
    PORTFOLIO_STRATEGY = "PORTFOLIO_STRATEGY"


class ConversationMessage(BaseModel):
    role: str
    content: str


class ConversationSummaryRequest(BaseModel):
    messages: list[ConversationMessage] = Field(default_factory=list)
    existing_summary: dict[str, Any] | None = Field(default=None, alias="existingSummary")
    locale: str = "zh-CN"

    model_config = {"populate_by_name": True}


class ConversationSummary(BaseModel):
    user_profile: dict[str, Any] = Field(default_factory=dict, alias="userProfile")
    research_context: dict[str, Any] = Field(default_factory=dict, alias="researchContext")
    open_questions: list[str] = Field(default_factory=list, alias="openQuestions")
    important_history: list[str] = Field(default_factory=list, alias="importantHistory")
    not_evidence: list[str] = Field(default_factory=list, alias="notEvidence")

    model_config = {"populate_by_name": True}


class ConversationSummaryResult(BaseModel):
    summary: ConversationSummary


class UserPreferences(BaseModel):
    preferred_locale: str = Field(default="zh-CN", alias="preferredLocale")
    default_market: str = Field(default="", alias="defaultMarket")
    risk_tolerance: str = Field(default="", alias="riskTolerance")
    time_horizon: str = Field(default="", alias="timeHorizon")
    report_style: str = Field(default="", alias="reportStyle")
    preferred_sectors: list[str] = Field(default_factory=list, alias="preferredSectors")
    excluded_sectors: list[str] = Field(default_factory=list, alias="excludedSectors")
    preferred_assets: list[str] = Field(default_factory=list, alias="preferredAssets")
    notes: str = ""
    enabled: bool = False

    model_config = {"populate_by_name": True}


class AgentRunRequest(BaseModel):
    run_id: UUID = Field(alias="runId")
    query: str = Field(min_length=1)
    locale: str = "zh-CN"
    conversation_messages: list[ConversationMessage] = Field(default_factory=list, alias="conversationMessages")
    user_preferences: UserPreferences = Field(default_factory=UserPreferences, alias="userPreferences")

    model_config = {"populate_by_name": True}


class CompanyCandidate(BaseModel):
    ticker: str
    exchange: str
    market: str
    confidence: float = Field(ge=0.0, le=1.0)


class CompanyMention(BaseModel):
    mention: str
    canonical_name: str = Field(alias="canonicalName")
    candidates: list[CompanyCandidate]
    needs_clarification: bool = Field(alias="needsClarification")
    ambiguity_reason: str | None = Field(default=None, alias="ambiguityReason")

    model_config = {"populate_by_name": True}


class IntentBreakdownItem(BaseModel):
    point: str
    planning_impact: str = Field(alias="planningImpact")

    model_config = {"populate_by_name": True}


class EntityCandidate(BaseModel):
    name: str
    identifier: str | None = None
    type_hint: str | None = Field(default=None, alias="typeHint")

    model_config = {"populate_by_name": True}


class ResearchEntity(BaseModel):
    mention: str
    resolution_status: str = Field(alias="resolutionStatus")
    best_guess: EntityCandidate | None = Field(default=None, alias="bestGuess")
    candidates: list[EntityCandidate] = Field(default_factory=list)
    notes: str = ""

    model_config = {"populate_by_name": True}


class QueryConstraint(BaseModel):
    kind: str
    raw_text: str = Field(alias="rawText")
    normalized_text: str = Field(default="", alias="normalizedText")
    needs_clarification: bool = Field(default=False, alias="needsClarification")

    model_config = {"populate_by_name": True}


class QueryUnderstanding(BaseModel):
    task_type: ResearchTaskType = Field(alias="taskType")
    intent_summary: str = Field(default="", alias="intentSummary")
    intent_breakdown: list[IntentBreakdownItem] = Field(default_factory=list, alias="intentBreakdown")
    entities: list[ResearchEntity] = Field(default_factory=list)
    companies: list[CompanyMention]
    time_horizon: str = Field(alias="timeHorizon")
    analysis_aspects: list[str] = Field(default_factory=list, alias="analysisAspects")
    comparison_mode: bool = Field(default=False, alias="comparisonMode")
    user_decision_context: str = Field(default="general_research", alias="userDecisionContext")
    requires_live_data: bool = Field(alias="requiresLiveData")
    output_style: str = Field(alias="outputStyle")
    constraints: list[str | QueryConstraint] = Field(default_factory=list)
    clarification_questions: list[str] = Field(alias="clarificationQuestions")
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = {"populate_by_name": True}


class ResearchPlanStep(BaseModel):
    step_id: str | None = Field(default=None, alias="stepId")
    tool_name: str | None = Field(default=None, alias="toolName")
    reason: str | None = None
    purpose: str | None = None
    tool_input: dict[str, Any] = Field(default_factory=dict, alias="toolInput")
    expected_evidence: str | None = Field(default=None, alias="expectedEvidence")
    expected_evidence_types: list[str] = Field(default_factory=list, alias="expectedEvidenceTypes")
    output_evidence_type: str = Field(default="", alias="outputEvidenceType")
    required: bool = True
    step: int | None = None
    tool: str | None = None
    expected_output: str | None = Field(default=None, alias="expectedOutput")

    model_config = {"populate_by_name": True}


class ResearchPlan(BaseModel):
    objective: str = ""
    steps: list[ResearchPlanStep] = Field(default_factory=list)


class AnswerSectionPlan(BaseModel):
    title: str
    purpose: str = ""

    model_config = {"populate_by_name": True}


class AnswerPlan(BaseModel):
    answer_goal: str = Field(default="", alias="answerGoal")
    sections: list[AnswerSectionPlan] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class PlanningDecision(BaseModel):
    answerability: str
    needs_tools: bool = Field(alias="needsTools")
    needs_clarification: bool = Field(alias="needsClarification")
    allowed_tools: list[str] = Field(default_factory=list, alias="allowedTools")
    evidence_needs: list[str] = Field(default_factory=list, alias="evidenceNeeds")
    clarification_questions: list[str] = Field(default_factory=list, alias="clarificationQuestions")
    max_steps: int = Field(default=6, ge=0, le=8, alias="maxSteps")
    rationale: str
    objective: str = ""
    steps: list[ResearchPlanStep] = Field(default_factory=list)
    answer_plan: AnswerPlan = Field(default_factory=AnswerPlan, alias="answerPlan")

    model_config = {"populate_by_name": True}


class AgentIntent(BaseModel):
    summary: str = ""
    entities: list[ResearchEntity] = Field(default_factory=list)
    companies: list[CompanyMention] = Field(default_factory=list)
    constraints: list[str | QueryConstraint] = Field(default_factory=list)
    needs_live_data: bool = Field(default=False, alias="needsLiveData")
    risk_level: str = Field(default="NORMAL", alias="riskLevel")

    model_config = {"populate_by_name": True}


class AgentPlanDecision(BaseModel):
    intent: AgentIntent
    answerability: str
    needs_tools: bool = Field(alias="needsTools")
    needs_clarification: bool = Field(alias="needsClarification")
    allowed_tools: list[str] = Field(default_factory=list, alias="allowedTools")
    evidence_needs: list[str] = Field(default_factory=list, alias="evidenceNeeds")
    clarification_questions: list[str] = Field(default_factory=list, alias="clarificationQuestions")
    max_steps: int = Field(default=6, ge=0, le=8, alias="maxSteps")
    rationale: str
    objective: str = ""
    steps: list[ResearchPlanStep] = Field(default_factory=list)
    answer_plan: AnswerPlan = Field(default_factory=AnswerPlan, alias="answerPlan")
    answer_policy: dict[str, Any] = Field(default_factory=dict, alias="answerPolicy")

    model_config = {"populate_by_name": True}

    def to_planning_decision(self) -> PlanningDecision:
        return PlanningDecision(
            answerability=self.answerability,
            needsTools=self.needs_tools,
            needsClarification=self.needs_clarification,
            allowedTools=self.allowed_tools,
            evidenceNeeds=self.evidence_needs,
            clarificationQuestions=self.clarification_questions,
            maxSteps=self.max_steps,
            rationale=self.rationale,
            objective=self.objective,
            steps=self.steps,
            answerPlan=self.answer_plan,
        )


class ReplanningDecision(BaseModel):
    action: str
    rationale: str
    additional_steps: list[ResearchPlanStep] = Field(default_factory=list, alias="additionalSteps")
    clarification_questions: list[str] = Field(default_factory=list, alias="clarificationQuestions")
    capability_gap: str = Field(default="", alias="capabilityGap")

    model_config = {"populate_by_name": True}


class ToolCallResult(BaseModel):
    tool_name: str = Field(alias="toolName")
    input: dict[str, Any]
    output: dict[str, Any]
    status: str
    latency_ms: int = Field(alias="latencyMs")

    model_config = {"populate_by_name": True}


class EvidenceItem(BaseModel):
    source_type: str = Field(alias="sourceType")
    source_name: str = Field(alias="sourceName")
    source_url: str | None = Field(default=None, alias="sourceUrl")
    title: str
    summary: str
    observed_at: str = Field(alias="observedAt")
    relevance: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_content: str = Field(alias="rawContent")

    model_config = {"populate_by_name": True}


class ArticleSummary(BaseModel):
    main_points: list[str] = Field(alias="mainPoints")
    facts: list[str]
    dates: list[str]
    companies: list[str]
    risks: list[str]
    limitations: list[str]

    model_config = {"populate_by_name": True}


class ReportCitation(BaseModel):
    id: int
    title: str
    source_name: str = Field(default="", alias="sourceName")
    url: str = ""
    supports: str = ""

    model_config = {"populate_by_name": True}


class ReportSection(BaseModel):
    title: str
    content: str
    citations: list[int] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ResearchReport(BaseModel):
    title: str
    answer_summary: str = Field(default="", alias="answerSummary")
    company_summary: str = Field(default="", alias="companySummary")
    question_understanding: str = Field(default="", alias="questionUnderstanding")
    key_findings: list[str] = Field(default_factory=list, alias="keyFindings")
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    evidence_summary: str = Field(default="", alias="evidenceSummary")
    uncertainty: str = ""
    citations: list[ReportCitation] = Field(default_factory=list)
    non_advisory_statement: str = Field(default="本报告仅用于研究辅助，不构成投资建议。", alias="nonAdvisoryStatement")
    sections: list[ReportSection] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @field_validator("citations", mode="before")
    @classmethod
    def normalize_legacy_citations(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        normalized = []
        for index, item in enumerate(value):
            if isinstance(item, str):
                normalized.append({
                    "id": index + 1,
                    "title": item,
                    "sourceName": "",
                    "url": item if item.startswith("http") else "",
                    "supports": "",
                })
            else:
                normalized.append(item)
        return normalized


class AnalystReasoning(BaseModel):
    thesis: str
    supporting_points: list[str] = Field(alias="supportingPoints")
    risks: list[str]
    valuation_notes: list[str] = Field(alias="valuationNotes")
    missing_data: list[str] = Field(alias="missingData")
    uncertainty: str

    model_config = {"populate_by_name": True}


class EvidenceDiagnostics(BaseModel):
    tool_call_count: int = Field(alias="toolCallCount")
    evidence_count: int = Field(alias="evidenceCount")
    failed_tools: list[str] = Field(default_factory=list, alias="failedTools")
    evidence_source_types: list[str] = Field(default_factory=list, alias="evidenceSourceTypes")
    planned_tool_names: list[str] = Field(default_factory=list, alias="plannedToolNames")
    executed_tool_names: list[str] = Field(default_factory=list, alias="executedToolNames")
    notes: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DataSufficiencyResult(BaseModel):
    status: str
    summary: str
    expected_evidence: list[str] = Field(default_factory=list, alias="expectedEvidence")
    available_evidence: list[str] = Field(default_factory=list, alias="availableEvidence")
    missing_evidence: list[str] = Field(default_factory=list, alias="missingEvidence")
    coverage_notes: list[str] = Field(default_factory=list, alias="coverageNotes")

    model_config = {"populate_by_name": True}


class EvidenceAssessment(BaseModel):
    summary: str
    usable_evidence: list[str] = Field(default_factory=list, alias="usableEvidence")
    missing_evidence: list[str] = Field(default_factory=list, alias="missingEvidence")
    failed_tools: list[str] = Field(default_factory=list, alias="failedTools")
    unsupported_questions: list[str] = Field(default_factory=list, alias="unsupportedQuestions")

    model_config = {"populate_by_name": True}


class ReportInstructions(BaseModel):
    tone: str = "cautious"
    must_say: list[str] = Field(default_factory=list, alias="mustSay")
    must_not_say: list[str] = Field(default_factory=list, alias="mustNotSay")
    revised_sections: list[AnswerSectionPlan] = Field(default_factory=list, alias="revisedSections")

    model_config = {"populate_by_name": True}


class EvidenceReasoningResult(BaseModel):
    answerability: str
    evidence_assessment: EvidenceAssessment = Field(alias="evidenceAssessment")
    data_sufficiency: DataSufficiencyResult = Field(alias="dataSufficiency")
    reasoning: AnalystReasoning
    report_instructions: ReportInstructions = Field(default_factory=ReportInstructions, alias="reportInstructions")

    model_config = {"populate_by_name": True}


class ValidationResult(BaseModel):
    passed: bool
    warnings: list[str]
    unsupported_claims: list[str] = Field(alias="unsupportedClaims")
    missing_data: list[str] = Field(alias="missingData")

    model_config = {"populate_by_name": True}


class ReflectionResult(BaseModel):
    passed: bool
    unsupported_claims: list[str] = Field(alias="unsupportedClaims")
    missing_data: list[str] = Field(alias="missingData")
    overconfident_statements: list[str] = Field(alias="overconfidentStatements")
    revision_instructions: list[str] = Field(alias="revisionInstructions")

    model_config = {"populate_by_name": True}


class AgentRunResult(BaseModel):
    run_id: UUID = Field(alias="runId")
    query: str
    locale: str
    run_status: str = Field(default="COMPLETED", alias="runStatus")
    runtime_warnings: list[str] = Field(default_factory=list, alias="runtimeWarnings")
    clarification_questions: list[str] = Field(default_factory=list, alias="clarificationQuestions")
    understanding: QueryUnderstanding | None = None
    planning_decision: PlanningDecision | None = Field(default=None, alias="planningDecision")
    plan: ResearchPlan | list[ResearchPlanStep]
    tool_calls: list[ToolCallResult] = Field(alias="toolCalls")
    evidence: list[EvidenceItem]
    replanning_decision: ReplanningDecision | None = Field(default=None, alias="replanningDecision")
    data_sufficiency: DataSufficiencyResult | None = Field(default=None, alias="dataSufficiency")
    evidence_reasoning: EvidenceReasoningResult | None = Field(default=None, alias="evidenceReasoning")
    reasoning: AnalystReasoning | None = None
    draft_report: ResearchReport | None = Field(default=None, alias="draftReport")
    reflection: ReflectionResult | None = None
    final_report: ResearchReport | None = Field(default=None, alias="finalReport")
    report: ResearchReport | None = None
    validation: ValidationResult | None = None

    model_config = {"populate_by_name": True}
