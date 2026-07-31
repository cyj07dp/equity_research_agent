const STORAGE_KEY = "equityResearch.currentConversationId";
const USER_KEY = "equityResearch.userName";

const state = {
  conversationId: new URLSearchParams(window.location.search).get("conversationId")
    || window.localStorage.getItem(STORAGE_KEY)
    || "",
  currentJobId: "",
  pollHandle: null,
  traceCache: new Map(),
  conversations: [],
  historyFilter: "",
  messages: [],
  currentTraces: new Map(),
  memorySuggestions: [],
  dismissedMemorySuggestions: new Set(),
};

const elements = {
  authButton: document.querySelector("#auth-button"),
  preferencesButton: document.querySelector("#preferences-button"),
  preferencesModal: document.querySelector("#preferences-modal"),
  preferencesForm: document.querySelector("#preferences-form"),
  preferencesCloseButton: document.querySelector("#preferences-close-button"),
  preferenceEnabled: document.querySelector("#preference-enabled"),
  preferenceMarket: document.querySelector("#preference-market"),
  preferenceRisk: document.querySelector("#preference-risk"),
  preferenceHorizon: document.querySelector("#preference-horizon"),
  preferenceStyle: document.querySelector("#preference-style"),
  preferenceSectors: document.querySelector("#preference-sectors"),
  preferenceExcludedSectors: document.querySelector("#preference-excluded-sectors"),
  preferenceAssets: document.querySelector("#preference-assets"),
  preferenceNotes: document.querySelector("#preference-notes"),
  userBadge: document.querySelector("#user-badge"),
  newConversationButton: document.querySelector("#new-conversation-button"),
  sidebarNewConversationButton: document.querySelector("#sidebar-new-conversation-button"),
  historyCount: document.querySelector("#history-count"),
  historySearch: document.querySelector("#history-search"),
  conversationList: document.querySelector("#conversation-list"),
  sendForm: document.querySelector("#send-form"),
  messageInput: document.querySelector("#message-input"),
  pageTitle: document.querySelector("#page-title"),
  messageArea: document.querySelector("#message-area"),
  messageCount: document.querySelector("#message-count"),
  messageList: document.querySelector("#message-list"),
};

assertRequiredElements(elements);
renderAuthState();

elements.authButton.addEventListener("click", () => {
  const currentName = window.localStorage.getItem(USER_KEY);
  if (currentName) {
    window.localStorage.removeItem(USER_KEY);
    renderAuthState();
    return;
  }
  const name = window.prompt("请输入昵称");
  if (name && name.trim()) {
    window.localStorage.setItem(USER_KEY, name.trim().slice(0, 24));
    renderAuthState();
  }
});

elements.preferencesButton.addEventListener("click", async () => {
  try {
    clearMessage();
    const preferences = await fetchJson("/api/me/preferences");
    fillPreferencesForm(preferences);
    elements.preferencesModal.classList.remove("hidden");
  } catch (error) {
    showMessage(error.message);
  }
});

elements.preferencesCloseButton.addEventListener("click", () => {
  elements.preferencesModal.classList.add("hidden");
});

elements.preferencesModal.addEventListener("click", (event) => {
  if (event.target === elements.preferencesModal) {
    elements.preferencesModal.classList.add("hidden");
  }
});

elements.preferencesForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    clearMessage();
    await fetchJson("/api/me/preferences", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(preferencesPayload()),
    });
    elements.preferencesModal.classList.add("hidden");
    showMessage("偏好已保存，之后的对话会作为默认约束使用。");
  } catch (error) {
    showMessage(error.message);
  }
});

elements.newConversationButton.addEventListener("click", () => {
  beginNewConversation();
});

elements.sidebarNewConversationButton.addEventListener("click", () => {
  beginNewConversation();
});

elements.historySearch.addEventListener("input", () => {
  state.historyFilter = elements.historySearch.value.trim();
  renderConversationList();
});

elements.conversationList.addEventListener("click", async (event) => {
  const item = event.target.closest("[data-conversation-id]");
  if (!item) {
    return;
  }
  const conversationId = item.getAttribute("data-conversation-id");
  if (!conversationId || conversationId === state.conversationId) {
    return;
  }
  stopPolling();
  clearMessage();
  try {
    const conversation = await loadConversation(conversationId);
    await applyConversation(conversation);
    startPolling();
  } catch (error) {
    showMessage(error.message);
  }
});

elements.messageList.addEventListener("click", async (event) => {
  const saveButton = event.target.closest("[data-memory-save]");
  const ignoreButton = event.target.closest("[data-memory-ignore]");
  if (!saveButton && !ignoreButton) {
    return;
  }
  const key = (saveButton || ignoreButton).getAttribute("data-suggestion-key");
  const suggestion = state.memorySuggestions.find((item) => memorySuggestionKey(item) === key);
  if (!suggestion) {
    return;
  }
  if (ignoreButton) {
    state.dismissedMemorySuggestions.add(key);
    renderMessagesFromState();
    return;
  }
  try {
    clearMessage();
    await saveMemorySuggestion(suggestion);
    state.dismissedMemorySuggestions.add(key);
    renderMessagesFromState();
    showMessage("投研偏好已更新，之后的对话会作为默认约束使用。");
  } catch (error) {
    showMessage(error.message);
  }
});

elements.sendForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = elements.messageInput.value.trim();
  if (!content) {
    showMessage("请输入研究问题或补充信息。");
    return;
  }

  try {
    clearMessage();
    setInputEnabled(false);
    const conversation = state.conversationId
      ? await appendMessage(content)
      : await createConversation(content);
    elements.messageInput.value = "";
    await applyConversation(conversation);
    startPolling();
  } catch (error) {
    showMessage(error.message);
  } finally {
    setInputEnabled(true);
    elements.messageInput.focus();
  }
});

if (state.conversationId) {
  refreshConversationList();
  loadConversation(state.conversationId)
    .then(async (conversation) => {
      await applyConversation(conversation);
      startPolling();
    })
    .catch((error) => {
      window.localStorage.removeItem(STORAGE_KEY);
      state.conversationId = "";
      state.currentJobId = "";
      showMessage(`无法恢复上次会话：${error.message}`);
      renderEmptyConversation();
    });
} else {
  refreshConversationList();
  renderEmptyConversation();
}

async function createConversation(query) {
  return fetchJson("/api/conversations", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({query}),
  });
}

async function appendMessage(content) {
  return fetchJson(`/api/conversations/${encodeURIComponent(state.conversationId)}/messages`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({content}),
  });
}

async function loadConversation(conversationId) {
  return fetchJson(`/api/conversations/${encodeURIComponent(conversationId)}`);
}

async function listConversations() {
  return fetchJson("/api/conversations");
}

async function applyConversation(conversation) {
  state.conversationId = conversation.conversationId || "";
  state.currentJobId = conversation.currentJobId || "";
  if (state.conversationId) {
    window.localStorage.setItem(STORAGE_KEY, state.conversationId);
  }
  updateUrl(state.conversationId);
  elements.pageTitle.textContent = conversation.title || "投研助手";

  const messages = conversation.messages || [];
  const traces = await tracesForMessages(messages);
  state.messages = messages;
  state.currentTraces = traces;
  state.memorySuggestions = conversation.memorySuggestions || [];
  renderMessagesFromState();
  await refreshConversationList();
}

async function tracesForMessages(messages) {
  const jobIds = [...new Set(messages.map((message) => message.jobId).filter(Boolean))];
  const entries = await Promise.all(jobIds.map(async (jobId) => {
    const trace = await traceForJob(jobId, {allowPending: true});
    return [jobId, trace];
  }));
  return new Map(entries);
}

async function traceForJob(jobId, {allowPending = false} = {}) {
  if (!jobId) {
    return null;
  }
  const cached = state.traceCache.get(jobId);
  if (cached && cached.__complete) {
    return cached;
  }
  try {
    const job = await fetchJson(`/api/research-jobs/${encodeURIComponent(jobId)}`);
    if (["PENDING", "RUNNING"].includes(job.status)) {
      const pendingTrace = {job, __complete: false};
      state.traceCache.set(jobId, pendingTrace);
      return pendingTrace;
    }
    const trace = await fetchJson(`/api/research-jobs/${encodeURIComponent(jobId)}/trace`);
    trace.job = job;
    trace.__complete = true;
    state.traceCache.set(jobId, trace);
    return trace;
  } catch (error) {
    if (allowPending) {
      return {error: error.message, __complete: false};
    }
    throw error;
  }
}

function renderEmptyConversation() {
  elements.pageTitle.textContent = "投研助手";
  state.conversationId = "";
  state.currentJobId = "";
  state.traceCache.clear();
  state.messages = [];
  state.currentTraces = new Map();
  state.memorySuggestions = [];
  window.localStorage.removeItem(STORAGE_KEY);
  updateUrl("");
  renderMessagesFromState();
  renderConversationList();
}

function renderMessagesFromState() {
  renderMessages(state.messages, state.currentTraces, state.memorySuggestions);
}

function renderMessages(messages, traces, memorySuggestions = []) {
  elements.messageCount.textContent = `${messages.length} 条消息`;
  if (!messages.length) {
    elements.messageList.innerHTML = emptyState("输入一个投研问题开始对话。");
    return;
  }
  const pendingAssistant = pendingAssistantFor(messages, traces);
  const suggestionPanel = memorySuggestionsHtml(memorySuggestions);
  elements.messageList.innerHTML = [
    ...messages.map((message) => messageHtml(message, traces.get(message.jobId))),
    pendingAssistant,
    suggestionPanel,
  ].join("");
  elements.messageList.scrollTop = elements.messageList.scrollHeight;
}

function pendingAssistantFor(messages, traces) {
  const lastMessage = messages.at(-1);
  if (!lastMessage || lastMessage.role !== "USER" || !lastMessage.jobId) {
    return "";
  }
  const trace = traces.get(lastMessage.jobId);
  if (!trace?.job || !["PENDING", "RUNNING"].includes(trace.job.status)) {
    return "";
  }
  return `
    <article class="chat-message assistant">
      <div class="message-head">
        <span class="role-badge">投研助手</span>
        <span class="meta-badge">分析中</span>
      </div>
      <div class="inline-status">正在分析，请稍等...</div>
    </article>
  `;
}

async function refreshConversationList() {
  try {
    state.conversations = await listConversations();
    renderConversationList();
  } catch (error) {
    state.conversations = [];
    renderConversationList();
  }
}

function renderConversationList() {
  const filter = state.historyFilter.toLowerCase();
  const conversations = state.conversations.filter((conversation) => {
    if (!filter) {
      return true;
    }
    return String(conversation.title || "").toLowerCase().includes(filter);
  });
  elements.historyCount.textContent = `${state.conversations.length} 个会话`;
  if (!conversations.length) {
    elements.conversationList.innerHTML = emptyState(filter ? "没有匹配的历史对话。" : "暂无历史对话。");
    return;
  }
  elements.conversationList.innerHTML = conversations.map((conversation) => {
    const id = conversation.conversationId || "";
    const active = id && id === state.conversationId;
    return `
      <button class="conversation-item ${active ? "active" : ""}" type="button" data-conversation-id="${escapeAttribute(id)}">
        <span class="conversation-title">${escapeHtml(conversation.title || "未命名会话")}</span>
        <span class="conversation-meta">
          <span>${escapeHtml(conversationStatusLabel(conversation.status))}</span>
          <span>${escapeHtml(relativeDate(conversation.updatedAt))}</span>
        </span>
      </button>
    `;
  }).join("");
}

function beginNewConversation() {
  stopPolling();
  clearMessage();
  renderEmptyConversation();
  elements.messageInput.focus();
}

function messageHtml(message, trace) {
  const role = message.role || "SYSTEM";
  const roleClass = role.toLowerCase();
  const createdAt = formatDateTime(message.createdAt);
  const isAssistant = role === "ASSISTANT";
  const report = trace?.report || null;
  const content = isAssistant && report
    ? reportConversationHtml(report, trace)
    : `<p class="message-content">${escapeHtml(message.content || "")}</p>`;
  const pendingBlock = isAssistant && trace?.job && ["PENDING", "RUNNING"].includes(trace.job.status)
    ? `<div class="inline-status">正在分析，请稍等...</div>`
    : "";
  const errorBlock = trace?.error
    ? `<div class="inline-error">${escapeHtml(trace.error)}</div>`
    : "";

  return `
    <article class="chat-message ${escapeAttribute(roleClass)}">
      <div class="message-head">
        <span class="role-badge">${roleLabel(role)}</span>
        <span class="meta-badge">${createdAt ? escapeHtml(createdAt) : ""}</span>
      </div>
      ${content}
      ${pendingBlock}
      ${errorBlock}
    </article>
  `;
}

function memorySuggestionsHtml(suggestions) {
  const activeSuggestions = (suggestions || [])
    .filter((suggestion) => !state.dismissedMemorySuggestions.has(memorySuggestionKey(suggestion)));
  if (!activeSuggestions.length) {
    return "";
  }
  return `
    <article class="memory-suggestion-card">
      <div>
        <p class="eyebrow">Preference</p>
        <h3>${activeSuggestions.some((item) => item.action === "UPDATE") ? "更新投研偏好？" : "保存为长期投研偏好？"}</h3>
        <p class="memory-suggestion-copy">我从你的问题中识别到可能的长期偏好。本轮回答仍会优先遵循当前问题，保存后只影响之后的对话。</p>
      </div>
      <div class="memory-suggestion-list">
        ${activeSuggestions.map(memorySuggestionItemHtml).join("")}
      </div>
    </article>
  `;
}

function memorySuggestionItemHtml(suggestion) {
  const key = memorySuggestionKey(suggestion);
  const actionText = suggestion.action === "UPDATE" ? "更新" : "保存";
  const current = suggestion.currentValue ? `当前：${displayMemoryValue(suggestion.field, suggestion.currentValue)}；` : "";
  return `
    <section class="memory-suggestion-item">
      <div>
        <h4>${escapeHtml(suggestion.label || suggestion.field || "偏好")}</h4>
        <p>${escapeHtml(current)}建议：${escapeHtml(suggestion.suggestedLabel || displayMemoryValue(suggestion.field, suggestion.suggestedValue))}</p>
        <span>${escapeHtml(suggestion.reason || "")}</span>
      </div>
      <div class="memory-suggestion-actions">
        <button type="button" data-memory-save data-suggestion-key="${escapeAttribute(key)}">${actionText}</button>
        <button type="button" class="secondary" data-memory-ignore data-suggestion-key="${escapeAttribute(key)}">忽略</button>
      </div>
    </section>
  `;
}

async function saveMemorySuggestion(suggestion) {
  const preferences = await fetchJson("/api/me/preferences");
  const payload = {
    preferredLocale: preferences.preferredLocale || "zh-CN",
    defaultMarket: preferences.defaultMarket || "",
    riskTolerance: preferences.riskTolerance || "",
    timeHorizon: preferences.timeHorizon || "",
    reportStyle: preferences.reportStyle || "",
    preferredSectors: preferences.preferredSectors || [],
    excludedSectors: preferences.excludedSectors || [],
    preferredAssets: preferences.preferredAssets || [],
    notes: preferences.notes || "",
    enabled: true,
  };
  if (Object.prototype.hasOwnProperty.call(payload, suggestion.field)) {
    payload[suggestion.field] = suggestion.suggestedValue || "";
  }
  await fetchJson("/api/me/preferences", {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
}

function memorySuggestionKey(suggestion) {
  return [
    suggestion.field || "",
    suggestion.currentValue || "",
    suggestion.suggestedValue || "",
    suggestion.action || "",
  ].join("|");
}

function displayMemoryValue(field, value) {
  const maps = {
    defaultMarket: {US: "美股", HK: "港股", CN: "A 股"},
    riskTolerance: {LOW: "保守", MEDIUM: "平衡", HIGH: "进取"},
    timeHorizon: {SHORT_TERM: "短期", MEDIUM_TERM: "中期", LONG_TERM: "长期"},
    reportStyle: {CONCISE: "简洁结论", DETAILED_MEMO: "详细备忘录", BEGINNER_FRIENDLY: "新手友好"},
  };
  return maps[field]?.[value] || value || "";
}

function reportConversationHtml(report, trace) {
  const rawTrace = trace?.rawAgentTrace || safeJson(report.rawJson);
  const finalReport = rawTrace.finalReport || {};
  const draftReport = rawTrace.draftReport || {};
  const dynamicSections = finalReport.sections || draftReport.sections || [];
  const answerSummary = finalReport.answerSummary
    || draftReport.answerSummary
    || report.answerSummary
    || fallbackAnswerSummary(report, dynamicSections, trace);
  const sections = dynamicSections.length
    ? dynamicSections
    : [
        {title: "回答", content: report.keyFindings || report.evidenceSummary || ""},
        {title: "需要注意", content: report.uncertainty || ""},
      ].filter((section) => section.content);
  const references = referencesFor(report, trace);

  return `
    <div class="assistant-report">
      <h3>${escapeHtml(report.title || "研究报告")}</h3>
      ${answerSummary ? `<div class="answer-summary"><strong>简短回答</strong><p>${escapeHtml(answerSummary)}</p></div>` : ""}
      ${sections.map((section) => `
        <section class="report-section">
          <h4>${escapeHtml(section.title || "分析")}</h4>
          <p>${escapeHtml(section.content || "")}</p>
        </section>
      `).join("")}
      ${referencesHtml(references)}
      ${report.nonAdvisoryStatement ? `<p class="non-advisory">${escapeHtml(report.nonAdvisoryStatement)}</p>` : ""}
    </div>
  `;
}

function referencesFor(report, trace) {
  if (Array.isArray(report.structuredCitations) && report.structuredCitations.length) {
    return report.structuredCitations.slice(0, 8).map((citation, index) => ({
      id: Number(citation.id || index + 1),
      title: citation.title || "参考来源",
      sourceName: citation.sourceName || "",
      sourceUrl: citation.url || "",
    }));
  }
  const items = (trace?.evidenceGroups || [])
    .flatMap((group) => group.items || [])
    .filter((item) => item.title || item.summary || item.sourceUrl);
  if (items.length) {
    return items.slice(0, 6).map((item) => ({
      id: items.indexOf(item) + 1,
      title: item.title || item.sourceName || "参考来源",
      sourceName: item.sourceName || localizeEvidenceText(item.sourceType || ""),
      sourceUrl: item.sourceUrl || "",
    }));
  }
  return splitCitations(report.citations).slice(0, 6).map((citation) => ({
    id: splitCitations(report.citations).indexOf(citation) + 1,
    title: citation,
    sourceName: "报告引用",
    sourceUrl: "",
  }));
}

function referencesHtml(references) {
  if (!references.length) {
    return "";
  }
  return `
    <section class="reference-section">
      <h4>参考文献</h4>
      <ol class="reference-list">
        ${references.map((reference, index) => referenceHtml(reference, index)).join("")}
      </ol>
    </section>
  `;
}

function referenceHtml(reference, index) {
  const label = [reference.sourceName, reference.title].filter(Boolean).join(" - ");
  const url = reference.sourceUrl || "";
  const displayId = Number(reference.id || index + 1);
  return `
    <li class="reference-item">
      <span class="reference-index">[${displayId}]</span>
      <div>
        <p class="reference-title">${escapeHtml(label || "参考来源")}</p>
        ${url ? `<a class="reference-url" href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">${escapeHtml(url)}</a>` : ""}
      </div>
    </li>
  `;
}

function splitCitations(value) {
  return String(value || "")
    .split(/\n|;|；/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function openQuestionsFor(trace) {
  if (!trace) {
    return [];
  }
  return firstNonEmptyList(
    trace.summary?.clarificationQuestions,
    trace.rawAgentTrace?.clarificationQuestions,
    trace.rawAgentTrace?.planningDecision?.clarificationQuestions,
    trace.rawAgentTrace?.evidenceReasoning?.reportInstructions?.mustSay,
  );
}

function startPolling() {
  stopPolling();
  if (!state.conversationId) {
    return;
  }
  state.pollHandle = window.setInterval(async () => {
    try {
      const conversation = await loadConversation(state.conversationId);
      await applyConversation(conversation);
      if (!state.currentJobId) {
        stopPolling();
        return;
      }
      const job = await fetchJson(`/api/research-jobs/${encodeURIComponent(state.currentJobId)}`);
      if (!["PENDING", "RUNNING"].includes(job.status)) {
        stopPolling();
        state.traceCache.delete(state.currentJobId);
        const refreshed = await loadConversation(state.conversationId);
        await applyConversation(refreshed);
      }
    } catch (error) {
      stopPolling();
      showMessage(error.message);
    }
  }, 2500);
}

function stopPolling() {
  if (state.pollHandle) {
    window.clearInterval(state.pollHandle);
    state.pollHandle = null;
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.message || payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function updateUrl(conversationId) {
  const url = new URL(window.location.href);
  url.searchParams.delete("conversationId");
  window.history.replaceState({}, "", url);
}

function setInputEnabled(enabled) {
  elements.messageInput.disabled = !enabled;
  elements.sendForm.querySelector("button").disabled = !enabled;
}

function fallbackAnswerSummary(report, sections, trace) {
  const openQuestions = openQuestionsFor(trace);
  const dataSufficiency = trace?.rawAgentTrace?.evidenceReasoning?.dataSufficiency
    || trace?.rawAgentTrace?.dataSufficiency
    || {};
  if (dataSufficiency.summary) {
    const nextStep = openQuestions.length ? "你补充相关信息后，我可以继续给出更有针对性的判断。" : "";
    return `${simplifyMixedLanguage(dataSufficiency.summary)}。${nextStep}`.trim();
  }
  const firstContent = sections.find((section) => section.content)?.content || report.evidenceSummary || "";
  if (!firstContent) {
    return "";
  }
  return shortText(firstContent, 150);
}

function simplifyMixedLanguage(value) {
  const text = String(value || "");
  if (/Based solely|provided evidence|buying opportunity|short-term/i.test(text)) {
    return "已基于现有证据完成分析：只能支持部分回答，不能形成明确买入判断";
  }
  return shortText(localizeEvidenceText(text), 140);
}

function localizeEvidenceText(value) {
  return String(value || "")
    .replaceAll(/\bMARKET_DATA\s+evidence\b/gi, "行情证据")
    .replaceAll(/\bFUNDAMENTALS\s+evidence\b/gi, "基本面证据")
    .replaceAll(/\bNEWS\s+evidence\b/gi, "新闻证据")
    .replaceAll(/\bSEC_FILINGS\s+evidence\b/gi, "SEC 公告证据")
    .replaceAll(/\bSEC_COMPANY_FACTS\s+evidence\b/gi, "SEC 财务事实证据")
    .replaceAll(/\bMARKET_DATA\b/g, "行情")
    .replaceAll(/\bFUNDAMENTALS\b/g, "基本面")
    .replaceAll(/\bNEWS\b/g, "新闻")
    .replaceAll(/\bSEC_FILINGS\b/g, "SEC 公告")
    .replaceAll(/\bSEC_COMPANY_FACTS\b/g, "SEC 财务事实")
    .replaceAll(/\bnews_search\b/g, "新闻搜索")
    .replaceAll(/\bmarket_price\b/g, "行情价格")
    .replaceAll(/\bfundamentals\b/g, "基本面")
    .replaceAll(/当前\s*evidence\s*/gi, "当前证据")
    .replaceAll(/\bevidence\b/gi, "证据")
    .replaceAll(/\s+证据/g, "证据")
    .replaceAll(/证据\s+/g, "证据")
    .replaceAll(/获得\s+/g, "获得")
    .replaceAll(/当前\s+证据/g, "当前证据")
    .replaceAll(/条\s+证据/g, "条证据");
}

function renderAuthState() {
  const name = window.localStorage.getItem(USER_KEY);
  if (!name) {
    elements.userBadge.classList.add("hidden");
    elements.userBadge.textContent = "";
    elements.authButton.textContent = "登录";
    return;
  }
  elements.userBadge.classList.remove("hidden");
  elements.userBadge.textContent = name;
  elements.authButton.textContent = "退出";
}

function fillPreferencesForm(preferences) {
  elements.preferenceEnabled.checked = Boolean(preferences.enabled);
  elements.preferenceMarket.value = preferences.defaultMarket || "";
  elements.preferenceRisk.value = preferences.riskTolerance || "";
  elements.preferenceHorizon.value = preferences.timeHorizon || "";
  elements.preferenceStyle.value = preferences.reportStyle || "";
  elements.preferenceSectors.value = (preferences.preferredSectors || []).join(", ");
  elements.preferenceExcludedSectors.value = (preferences.excludedSectors || []).join(", ");
  elements.preferenceAssets.value = (preferences.preferredAssets || []).join(", ");
  elements.preferenceNotes.value = preferences.notes || "";
}

function preferencesPayload() {
  return {
    preferredLocale: "zh-CN",
    defaultMarket: elements.preferenceMarket.value,
    riskTolerance: elements.preferenceRisk.value,
    timeHorizon: elements.preferenceHorizon.value,
    reportStyle: elements.preferenceStyle.value,
    preferredSectors: commaList(elements.preferenceSectors.value),
    excludedSectors: commaList(elements.preferenceExcludedSectors.value),
    preferredAssets: commaList(elements.preferenceAssets.value),
    notes: elements.preferenceNotes.value.trim(),
    enabled: elements.preferenceEnabled.checked,
  };
}

function commaList(value) {
  return String(value || "")
    .split(/,|，/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 20);
}

function conversationStatusLabel(status) {
  return {
    RUNNING: "分析中",
    WAITING_USER: "待补充",
    ACTIVE: "已完成",
    FAILED: "失败",
  }[status] || "会话";
}

function relativeDate(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const diffMs = Date.now() - date.getTime();
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (diffMs < minute) {
    return "刚刚";
  }
  if (diffMs < hour) {
    return `${Math.floor(diffMs / minute)} 分钟前`;
  }
  if (diffMs < day) {
    return `${Math.floor(diffMs / hour)} 小时前`;
  }
  if (diffMs < 7 * day) {
    return `${Math.floor(diffMs / day)} 天前`;
  }
  return date.toLocaleDateString("zh-CN");
}

function shortText(value, limit) {
  const text = String(value || "").replaceAll(/\s+/g, " ").trim();
  if (text.length <= limit) {
    return text;
  }
  return `${text.slice(0, limit)}...`;
}

function firstNonEmptyList(...values) {
  for (const value of values) {
    if (Array.isArray(value) && value.length) {
      return value.filter(Boolean);
    }
  }
  return [];
}

function showMessage(message) {
  elements.messageArea.classList.remove("hidden");
  elements.messageArea.textContent = message;
}

function clearMessage() {
  elements.messageArea.classList.add("hidden");
  elements.messageArea.textContent = "";
}

function emptyState(text) {
  return `<p class="summary">${escapeHtml(text)}</p>`;
}

function roleLabel(role) {
  if (role === "USER") {
    return "你";
  }
  if (role === "ASSISTANT") {
    return "投研助手";
  }
  return escapeHtml(role);
}

function formatDateTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", {hour12: false});
}

function formatDate(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleDateString("zh-CN");
}

function safeJson(value) {
  if (!value) {
    return {};
  }
  try {
    return typeof value === "string" ? JSON.parse(value) : value;
  } catch {
    return {};
  }
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

function assertRequiredElements(elementMap) {
  const missing = Object.entries(elementMap)
    .filter(([, element]) => !element)
    .map(([name]) => name);
  if (!missing.length) {
    return;
  }
  const message = `Conversation page initialization failed. Missing DOM nodes: ${missing.join(", ")}`;
  document.body.innerHTML = `<main class="shell"><section class="message-area">${escapeHtml(message)}</section></main>`;
  throw new Error(message);
}
