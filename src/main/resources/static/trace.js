const state = {
  jobId: new URLSearchParams(window.location.search).get("jobId") || "",
  pollHandle: null,
};

const elements = {
  queryForm: document.querySelector("#query-form"),
  jobForm: document.querySelector("#job-form"),
  queryInput: document.querySelector("#query-input"),
  jobIdInput: document.querySelector("#job-id-input"),
  currentJobId: document.querySelector("#current-job-id"),
  pageTitle: document.querySelector("#page-title"),
  statusPill: document.querySelector("#status-pill"),
  messageArea: document.querySelector("#message-area"),
  metricSuccess: document.querySelector("#metric-success"),
  metricFailure: document.querySelector("#metric-failure"),
  metricEvidence: document.querySelector("#metric-evidence"),
  metricCompany: document.querySelector("#metric-company"),
  clarificationPanel: document.querySelector("#clarification-panel"),
  clarificationList: document.querySelector("#clarification-list"),
  stageCount: document.querySelector("#stage-count"),
  stageTimeline: document.querySelector("#stage-timeline"),
  toolCount: document.querySelector("#tool-count"),
  toolSteps: document.querySelector("#tool-steps"),
  evidenceGroupCount: document.querySelector("#evidence-group-count"),
  evidenceGroups: document.querySelector("#evidence-groups"),
  reportState: document.querySelector("#report-state"),
  reportPanel: document.querySelector("#report-panel"),
  rawTrace: document.querySelector("#raw-trace"),
};

elements.queryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = elements.queryInput.value.trim();
  if (!query) {
    showMessage("请输入研究问题。");
    return;
  }
  try {
    clearMessage();
    setStatus("CREATING", "muted");
    const response = await fetch("/api/research-jobs", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({query}),
    });
    const payload = await parseJsonResponse(response);
    state.jobId = payload.jobId;
    elements.jobIdInput.value = state.jobId;
    setCurrentJob(state.jobId);
    updateUrl(state.jobId);
    await loadJobAndTrace(state.jobId);
    startPolling(state.jobId);
  } catch (error) {
    showMessage(error.message);
    setStatus("ERROR", "danger");
  }
});

elements.jobForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const jobId = elements.jobIdInput.value.trim();
  if (!jobId) {
    showMessage("请输入 jobId。");
    return;
  }
  try {
    clearMessage();
    stopPolling();
    state.jobId = jobId;
    setCurrentJob(jobId);
    updateUrl(jobId);
    await loadJobAndTrace(jobId);
    startPolling(jobId);
  } catch (error) {
    showMessage(error.message);
    setStatus("ERROR", "danger");
  }
});

if (state.jobId) {
  elements.jobIdInput.value = state.jobId;
  setCurrentJob(state.jobId);
  loadJobAndTrace(state.jobId).then(() => startPolling(state.jobId)).catch((error) => {
    showMessage(error.message);
    setStatus("ERROR", "danger");
  });
}

async function loadJobAndTrace(jobId) {
  const job = await fetchJson(`/api/research-jobs/${encodeURIComponent(jobId)}`);
  renderJob(job);

  if (job.status === "PENDING" || job.status === "RUNNING") {
    renderPendingTrace(job);
    return job;
  }

  const trace = await fetchJson(`/api/research-jobs/${encodeURIComponent(jobId)}/trace`);
  renderTrace(trace, job);
  return job;
}

function startPolling(jobId) {
  stopPolling();
  state.pollHandle = window.setInterval(async () => {
    try {
      const job = await loadJobAndTrace(jobId);
      if (!["PENDING", "RUNNING"].includes(job.status)) {
        stopPolling();
      }
    } catch (error) {
      stopPolling();
      showMessage(error.message);
      setStatus("ERROR", "danger");
    }
  }, 2500);
}

function stopPolling() {
  if (state.pollHandle) {
    window.clearInterval(state.pollHandle);
    state.pollHandle = null;
  }
}

function renderJob(job) {
  elements.pageTitle.textContent = job.query || "研究任务";
  setCurrentJob(job.jobId);
  setStatus(job.status, statusClass(job.status));
  renderClarification(job.clarificationQuestions || []);
}

function renderPendingTrace(job) {
  elements.metricSuccess.textContent = "0";
  elements.metricFailure.textContent = "0";
  elements.metricEvidence.textContent = "0";
  elements.metricCompany.textContent = "-";
  elements.stageCount.textContent = "1 stage";
  elements.stageTimeline.innerHTML = stageHtml({
    name: "job_queue",
    status: job.status === "RUNNING" ? "success" : "pending",
    summary: job.status === "RUNNING" ? "任务已进入 Agent 执行阶段。" : "任务已创建，等待执行。",
  });
  elements.toolCount.textContent = "0 calls";
  elements.toolSteps.innerHTML = emptyState("暂无工具调用。");
  elements.evidenceGroupCount.textContent = "0 groups";
  elements.evidenceGroups.innerHTML = emptyState("暂无证据。");
  elements.reportState.textContent = "pending";
  elements.reportPanel.innerHTML = emptyState("报告尚未生成。");
  elements.rawTrace.textContent = "{}";
}

function renderTrace(trace, job) {
  const summary = trace.summary || {};
  const report = trace.report || null;
  const stages = trace.stages || [];
  const evidenceGroups = trace.evidenceGroups || [];
  const toolSteps = stages.flatMap((stage) => stage.steps || []);
  const rawTrace = trace.rawAgentTrace || {};

  elements.metricSuccess.textContent = String(summary.toolSuccessCount ?? 0);
  elements.metricFailure.textContent = String(summary.toolFailureCount ?? 0);
  elements.metricEvidence.textContent = String(summary.evidenceCount ?? 0);
  elements.metricCompany.textContent = subjectLabel(summary);

  renderClarification(firstNonEmptyList(
    job.clarificationQuestions,
    summary.clarificationQuestions,
    rawTrace.clarificationQuestions,
    rawTrace.planningDecision?.clarificationQuestions,
  ), rawTrace.understanding);
  renderWarnings(summary.warnings || []);

  elements.stageCount.textContent = `${stages.length} stages`;
  elements.stageTimeline.innerHTML = stages.length
    ? stages.map(stageHtml).join("")
    : emptyState("暂无阶段信息。");

  elements.toolCount.textContent = `${toolSteps.length} calls`;
  elements.toolSteps.innerHTML = toolSteps.length
    ? toolSteps.map(toolStepHtml).join("")
    : emptyState("暂无工具调用。");

  elements.evidenceGroupCount.textContent = `${evidenceGroups.length} groups`;
  elements.evidenceGroups.innerHTML = evidenceGroups.length
    ? evidenceGroups.map(evidenceGroupHtml).join("")
    : emptyState("暂无证据。");

  if (job.status === "NEEDS_CLARIFICATION" || rawTrace.runStatus === "NEEDS_CLARIFICATION") {
    elements.reportState.textContent = "waiting clarification";
    elements.reportPanel.innerHTML = emptyState("等待用户补充信息，尚未生成最终投研报告。");
  } else {
    elements.reportState.textContent = report ? "saved" : "pending";
    elements.reportPanel.innerHTML = report ? reportHtml(report) : emptyState("报告尚未生成。");
  }
  elements.rawTrace.textContent = JSON.stringify(rawTrace, null, 2);
}

function renderClarification(questions, understanding = null) {
  if (!questions.length) {
    elements.clarificationPanel.classList.add("hidden");
    elements.clarificationList.innerHTML = "";
    return;
  }
  elements.clarificationPanel.classList.remove("hidden");
  const understandingItems = clarificationUnderstandingItems(understanding);
  elements.clarificationList.innerHTML = [
    ...understandingItems,
    ...questions.map((question) => `<li><strong>需要回答：</strong>${escapeHtml(question)}</li>`),
  ].join("");
}

function clarificationUnderstandingItems(understanding) {
  if (!understanding) {
    return [];
  }
  const items = [];
  if (understanding.intentSummary) {
    items.push(`<li><strong>已理解：</strong>${escapeHtml(understanding.intentSummary)}</li>`);
  }
  const entities = understanding.entities || [];
  entities.forEach((entity) => {
    const status = entity.resolutionStatus || "UNKNOWN";
    const guess = entity.bestGuess?.identifier || entity.bestGuess?.name || "";
    const candidates = (entity.candidates || [])
      .map((candidate) => candidate.identifier || candidate.name)
      .filter(Boolean)
      .join(" / ");
    const suffix = guess || candidates || entity.notes || "";
    items.push(`<li><strong>${escapeHtml(status)}：</strong>${escapeHtml(entity.mention || "对象")}${suffix ? `（${escapeHtml(suffix)}）` : ""}</li>`);
  });
  return items;
}

function renderWarnings(warnings) {
  if (!warnings.length) {
    clearMessage();
    return;
  }
  elements.messageArea.classList.remove("hidden");
  elements.messageArea.innerHTML = warnings.map((warning) => `<div>${escapeHtml(warning)}</div>`).join("");
}

function stageHtml(stage) {
  const status = stage.status || "pending";
  const details = stageDetailsHtml(stage);
  return `
    <article class="stage-item">
      <span class="stage-dot ${escapeHtml(status)}"></span>
      <div>
        <div class="stage-title">
          <strong>${stageLabel(stage.name)}</strong>
          <span class="badge">${escapeHtml(status)}</span>
        </div>
        <p class="summary">${escapeHtml(stage.summary || "")}</p>
        ${details}
      </div>
    </article>
  `;
}

function stageDetailsHtml(stage) {
  const details = stage.details || {};
  if (stage.name === "planning_decision" && details.planningDecision) {
    const decision = details.planningDecision;
    const answerPlan = decision.answerPlan || {};
    return `
      <div class="stage-details">
        ${detailBadge("answerability", decision.answerability)}
        ${detailBadge("needsTools", String(Boolean(decision.needsTools)))}
        ${detailBadge("needsClarification", String(Boolean(decision.needsClarification)))}
        ${detailBadge("tools", (decision.allowedTools || []).join(", "))}
        ${detailBadge("answerGoal", answerPlan.answerGoal)}
        ${detailBadge("sections", (answerPlan.sections || []).map((section) => section.title).join(" / "))}
      </div>
    `;
  }
  if (stage.name === "planning" && details.plan?.steps) {
    const tools = details.plan.steps.map((step) => step.toolName || step.tool).filter(Boolean).join(", ");
    return `<div class="stage-details">${detailBadge("steps", String(details.plan.steps.length))}${detailBadge("tools", tools)}</div>`;
  }
  if (stage.name === "evidence_reasoning") {
    const evidenceReasoning = details.evidenceReasoning || {};
    const sufficiency = evidenceReasoning.dataSufficiency || details.dataSufficiency || {};
    const assessment = evidenceReasoning.evidenceAssessment || {};
    const reasoning = evidenceReasoning.reasoning || details.reasoning || {};
    return `
      <div class="stage-details">
        ${detailBadge("status", sufficiency.status)}
        ${detailBadge("expected", (sufficiency.expectedEvidence || []).join(", "))}
        ${detailBadge("missing", (sufficiency.missingEvidence || []).join(", "))}
        ${detailBadge("unsupported", (assessment.unsupportedQuestions || []).join(", "))}
        ${detailBadge("thesis", reasoning.thesis)}
      </div>
    `;
  }
  return "";
}

function toolStepHtml(step) {
  const error = step.error ? `<div class="tool-error">${escapeHtml(step.error)}</div>` : "";
  return `
    <article class="tool-item">
      <div class="tool-title">
        <strong>${escapeHtml(step.toolName || "unknown_tool")}</strong>
        <span class="badge">${escapeHtml(step.status || "UNKNOWN")}</span>
      </div>
      <p class="summary">${escapeHtml(step.summary || "")}</p>
      ${error}
      <div class="tool-meta">
        <span class="badge">${Number(step.latencyMs || 0)} ms</span>
        <span class="badge">input ${objectSize(step.input)}</span>
        <span class="badge">output ${objectSize(step.output)}</span>
      </div>
    </article>
  `;
}

function evidenceGroupHtml(group) {
  const items = group.items || [];
  return `
    <div class="evidence-group">
      <div class="group-title">
        <span>${escapeHtml(group.sourceType || "UNKNOWN")}</span>
        <span>${items.length} items</span>
      </div>
      ${items.map(evidenceItemHtml).join("")}
    </div>
  `;
}

function evidenceItemHtml(item) {
  const link = item.sourceUrl
    ? `<a href="${escapeAttribute(item.sourceUrl)}" target="_blank" rel="noreferrer">来源链接</a>`
    : "";
  const ragChunks = item.sourceType === "SEC_RAG" ? secRagChunksHtml(item.rawContent) : "";
  return `
    <article class="evidence-item">
      <div class="evidence-title">
        <strong>${escapeHtml(item.title || item.sourceName || "Evidence")}</strong>
        <span class="badge">${escapeHtml(String(item.confidence ?? "-"))}</span>
      </div>
      <p class="summary">${escapeHtml(item.summary || "")}</p>
      ${ragChunks}
      ${link}
    </article>
  `;
}

function secRagChunksHtml(rawContent) {
  const raw = safeJson(rawContent);
  const chunks = Array.isArray(raw.retrievedChunks) ? raw.retrievedChunks.slice(0, 3) : [];
  if (!chunks.length) {
    return "";
  }
  return `
    <div class="rag-chunks">
      ${chunks.map((chunk, index) => secRagChunkHtml(chunk, index)).join("")}
    </div>
    <details class="raw-evidence">
      <summary>查看 SEC RAG raw JSON</summary>
      <pre>${escapeHtml(JSON.stringify(raw, null, 2))}</pre>
    </details>
  `;
}

function secRagChunkHtml(chunk, index) {
  const matchedTerms = Array.isArray(chunk.matchedTerms) ? chunk.matchedTerms.join(", ") : "";
  const sourceUrl = chunk.sourceUrl || "";
  const sourceLink = sourceUrl
    ? `<a href="${escapeAttribute(sourceUrl)}" target="_blank" rel="noreferrer">sec.gov</a>`
    : "";
  return `
    <div class="rag-chunk">
      <div class="stage-details">
        ${detailBadge("chunk", String(index + 1))}
        ${detailBadge("section", chunk.sectionHint)}
        ${detailBadge("score", chunk.score)}
        ${detailBadge("matched", matchedTerms)}
        ${sourceLink}
      </div>
      <p class="summary">${escapeHtml(chunk.text || "")}</p>
    </div>
  `;
}

function reportHtml(report) {
  const rawTrace = safeJson(report.rawJson);
  const dynamicSections = rawTrace.finalReport?.sections || rawTrace.draftReport?.sections || [];
  if (dynamicSections.length) {
    return [
      reportSectionHtml("标题", report.title),
      reportSectionHtml("研究对象", subjectLabel(report)),
      ...dynamicSections.map((section) => reportSectionHtml(section.title, section.content)),
      reportSectionHtml("引用", report.citations),
      reportSectionHtml("声明", report.nonAdvisoryStatement),
    ].join("");
  }
  const sections = [
    ["标题", report.title],
    ["研究对象", subjectLabel(report)],
    ["对象概览", report.subjectSummary],
    ["问题理解", report.questionUnderstanding],
    ["报告正文", report.keyFindings],
    ["证据摘要", report.evidenceSummary],
    ["不确定性", report.uncertainty],
    ["引用", report.citations],
    ["声明", report.nonAdvisoryStatement],
  ].filter(([, value]) => value);

  return sections.map(([title, value]) => reportSectionHtml(title, value)).join("");
}

function reportSectionHtml(title, value) {
  if (!value) {
    return "";
  }
  return `
    <section class="report-section">
      <h4>${escapeHtml(title)}</h4>
      <p>${escapeHtml(value)}</p>
    </section>
  `;
}

function subjectLabel(value) {
  const name = value.subjectName || "";
  const identifier = value.subjectIdentifier || "";
  const type = value.subjectType || "";
  if (!name && !identifier && !type) {
    return "-";
  }
  const suffix = [identifier, type].filter(Boolean).join(" / ");
  return suffix ? `${name || "研究对象"} (${suffix})` : name;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  return parseJsonResponse(response);
}

async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.message || payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function setCurrentJob(jobId) {
  elements.currentJobId.textContent = jobId || "未选择";
}

function setStatus(status, className) {
  elements.statusPill.textContent = status || "IDLE";
  elements.statusPill.className = `status-pill ${className || "muted"}`;
}

function statusClass(status) {
  if (status === "SUCCEEDED") {
    return "success";
  }
  if (status === "FAILED") {
    return "danger";
  }
  if (status === "NEEDS_CLARIFICATION") {
    return "warning";
  }
  return "muted";
}

function showMessage(message) {
  elements.messageArea.classList.remove("hidden");
  elements.messageArea.textContent = message;
}

function clearMessage() {
  elements.messageArea.classList.add("hidden");
  elements.messageArea.textContent = "";
}

function updateUrl(jobId) {
  const url = new URL(window.location.href);
  url.searchParams.set("jobId", jobId);
  window.history.replaceState({}, "", url);
}

function stageLabel(name) {
  return {
    query_understanding: "Agent Planner",
    agent_planning: "Agent Planner",
    planning: "Agent Planner",
    planning_decision: "Agent Planner",
    tool_execution: "Tool Execution",
    evidence: "Evidence",
    data_sufficiency: "Evidence Audit",
    evidence_reasoning: "Evidence Audit",
    conditional_replanning: "Conditional Replanner",
    reflection: "Critic Review",
    final_report: "Final Report",
    job_queue: "Job Queue",
  }[name] || name || "Stage";
}

function objectSize(value) {
  if (!value || typeof value !== "object") {
    return 0;
  }
  return Object.keys(value).length;
}

function firstNonEmptyList(...lists) {
  for (const list of lists) {
    if (Array.isArray(list) && list.length > 0) {
      return list;
    }
  }
  return [];
}

function detailBadge(label, value) {
  if (value === undefined || value === null || String(value).trim() === "") {
    return "";
  }
  return `<span class="badge detail-badge">${escapeHtml(label)}: ${escapeHtml(value)}</span>`;
}

function safeJson(value) {
  if (!value) {
    return {};
  }
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}

function emptyState(text) {
  return `<p class="summary">${escapeHtml(text)}</p>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
