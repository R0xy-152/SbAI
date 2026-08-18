const form = document.querySelector("#player-form");
const input = document.querySelector("#player-message");
const dialogueText = document.querySelector("#dialogue-text");
const status = document.querySelector("#form-status");
const characterSprite = document.querySelector("#character-sprite");
const characterName = document.querySelector("#character-name");
const sendButton = form.querySelector("button[type='submit']");

// TV-16: character switcher + History view (docs/01 §7, §10.2, §18).
const historyToggle = document.querySelector("#history-toggle");
const historyPanel = document.querySelector("#history-panel");
const historyList = document.querySelector("#history-list");
const evidenceToggle = document.querySelector("#evidence-toggle");
const evidencePanel = document.querySelector("#evidence-panel");
const evidenceList = document.querySelector("#evidence-list");
const evidenceEmpty = document.querySelector("#evidence-empty");
const switchButtons = {
  deepseek: document.querySelector("#switch-deepseek"),
  claude: document.querySelector("#switch-claude"),
  chatgpt: document.querySelector("#switch-chatgpt"),
  doubao: document.querySelector("#switch-doubao"),
};

const investigationButtons =
  typeof document.querySelectorAll === "function"
    ? document.querySelectorAll("[data-hotspot-id]")
    : [];
const paperPanel = document.querySelector("#paper-panel");
const paperClose = document.querySelector("#paper-close");
const rubbingSurface = document.querySelector("#rubbing-surface");
const rubbingCanvas = document.querySelector("#rubbing-canvas");
const deductionForm = document.querySelector("#deduction-form");
const deductionInput = document.querySelector("#deduction-message");
const claudePrivateInterview = document.querySelector("#claude-private-interview");
const claudePrivateSubmit = document.querySelector("#claude-private-submit");
const doubaoPrivateInterview = document.querySelector("#doubao-private-interview");
const doubaoPrivateSubmit = document.querySelector("#doubao-private-submit");
const gptPrivateInterview = document.querySelector("#gpt-private-interview");
const gptPrivateSubmit = document.querySelector("#gpt-private-submit");

// TV-16: per-character display (docs/01 §10.1-10.2). Claude's portrait is a
// temporary validation fixture (docs/06 §28: Fixture ≠ Production Content).
const CHARACTERS = {
  deepseek: {
    name: "DeepSeek",
    sprite: "../char/deepseek/pic/deepseek_main.png",
  },
  claude: {
    name: "Claude",
    sprite: "./public/characters/claude-placeholder.svg",
  },
  chatgpt: {
    name: "ChatGPT",
    sprite: "./public/characters/claude-placeholder.svg",
  },
  doubao: {
    name: "豆包",
    sprite: "./public/characters/claude-placeholder.svg",
  },
};

// TV-16: the player's explicit speaker choice (docs/04 §61: deciding WHO
// responds from natural language is a Backend decision; the UI only forwards
// the player's pick). null = use the backend's current character.
let selectedCharacter = null;

// TV-14: the session id is kept across a page refresh so the backend can
// restore the same game (Session Restore). localStorage is guarded because
// the Node DOM-stub tests have no browser storage.
function readSessionId() {
  if (typeof localStorage === "undefined") return null;
  try {
    return localStorage.getItem("gal_session_id") || null;
  } catch (_error) {
    return null;
  }
}

function writeSessionId(id) {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem("gal_session_id", id);
  } catch (_error) {
    // storage unavailable (e.g. private mode): the session still works for
    // this page load, it just does not survive a refresh.
  }
}

let sessionId = readSessionId();

// TV-03: when served by the FastAPI backend, use a same-origin /api/chat URL;
// when opened directly as a file, fall back to the local backend origin.
const API_BASE = (() => {
  if (
    typeof window !== "undefined" &&
    window.location &&
    window.location.protocol === "file:"
  ) {
    return "http://localhost:8000";
  }
  return "";
})();

const animationClasses = {
  fade_in: "is-fading-in",
  fade_out: "is-fading-out",
  shake: "is-shaking",
};

const expressionNames = new Set(["normal", "alert"]);

function replayAnimation(className, afterAnimation) {
  characterSprite.classList.remove(className);
  void characterSprite.offsetWidth;
  characterSprite.classList.add(className);
  characterSprite.addEventListener(
    "animationend",
    () => {
      characterSprite.classList.remove(className);
      afterAnimation?.();
    },
    { once: true },
  );
}

function applyPresentationDirective({ character, animation, expression } = {}) {
  if (character !== characterSprite.dataset.character) {
    return { applied: false, reason: "unknown_character" };
  }

  if (expression !== undefined) {
    if (!expressionNames.has(expression)) {
      return { applied: false, reason: "unknown_expression" };
    }
    characterSprite.dataset.expression = expression;
  }

  if (animation !== undefined) {
    const animationClass = animationClasses[animation];
    if (!animationClass) {
      return { applied: false, reason: "unknown_animation" };
    }

    if (animation === "fade_in") {
      characterSprite.classList.remove("is-hidden");
    }
    replayAnimation(animationClass, () => {
      if (animation === "fade_out") {
        characterSprite.classList.add("is-hidden");
      }
    });
  }

  return { applied: true };
}

if (typeof window !== "undefined") {
  window.galPresentation = { apply: applyPresentationDirective };
}

// TV-16: switch which character is displayed on stage (docs/01 §10.2). With
// fadeIn it also plays the allowed fade_in animation (docs/03 §44.1).
function setCharacter(characterId, { fadeIn = false } = {}) {
  const character = CHARACTERS[characterId];
  if (!character) return;
  characterSprite.dataset.character = characterId;
  characterSprite.src = character.sprite;
  if (fadeIn) {
    window.galPresentation.apply({ character: characterId, animation: "fade_in" });
  }
}

// TV-16: the dialogue box names whoever actually spoke (docs/01 §7 当前发言
// 角色正确), independent of who the stage sprite shows.
function setSpeaker(characterId) {
  const character = CHARACTERS[characterId];
  if (!character) return;
  characterName.textContent = character.name;
}

// TV-16: the player's explicit speaker pick for the next message.
function selectCharacter(characterId) {
  if (!CHARACTERS[characterId]) return;
  selectedCharacter = characterId;
  for (const [id, button] of Object.entries(switchButtons)) {
    if (button) button.classList.toggle("is-active", id === characterId);
  }
  status.textContent = `已切换：${CHARACTERS[characterId].name}。`;
}

for (const [id, button] of Object.entries(switchButtons)) {
  if (button) {
    button.addEventListener("click", () => selectCharacter(id));
  }
}

// TV-16: apply a backend reply's presentation (docs/03 §13.6). Returns the
// character the stage was switched to by SHOW_CHARACTER, if any.
function applyPresentation(directives) {
  let presentedCharacter = null;
  for (const directive of directives || []) {
    const space = directive.indexOf(" ");
    const kind = space === -1 ? directive : directive.slice(0, space);
    const target = space === -1 ? "" : directive.slice(space + 1);
    if (kind === "SHOW_CHARACTER") {
      presentedCharacter = target;
      setCharacter(target, { fadeIn: true });
    } else if (kind === "HIDE_CHARACTER") {
      characterSprite.classList.add("is-hidden");
    } else if (kind === "PLAY_ANIMATION" && target) {
      window.galPresentation.apply({
        character: characterSprite.dataset.character,
        animation: target,
      });
    }
    // FADE / FADE_IN / FADE_OUT / PLAY_EFFECT: presentation details the
    // current fixture does not need to render.
  }
  return presentedCharacter;
}

// TV-16: History view (docs/01 §18) — fetch the session's dialogue from the
// backend and render it in order.
async function loadHistory() {
  if (!sessionId) return;
  const response = await fetch(
    `${API_BASE}/api/chat/history?session_id=${encodeURIComponent(sessionId)}`,
  );
  if (!response.ok) {
    status.textContent = "历史加载失败。";
    return;
  }
  const data = await response.json();
  renderHistory(data.messages || []);
}

function renderHistory(messages) {
  historyList.replaceChildren();
  for (const message of messages) {
    const item = document.createElement("li");
    const speaker =
      message.role === "player"
        ? "Player"
        : (CHARACTERS[message.character_id]?.name ||
          message.character_id ||
          "未知");
    item.textContent = `${speaker}：${message.content}`;
    historyList.appendChild(item);
  }
}

if (historyToggle) {
  historyToggle.addEventListener("click", async () => {
    if (historyPanel.hidden) {
      await loadHistory();
      historyPanel.hidden = false;
      historyToggle.textContent = "收起历史";
    } else {
      historyPanel.hidden = true;
      historyToggle.textContent = "查看历史";
    }
  });
}

async function sendMessage(message) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      character_id: selectedCharacter,
    }),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
  sessionId = data.session_id;
  writeSessionId(sessionId);
  return data;
}

async function sendInvestigationAction(action, hotspotId) {
  const response = await fetch(`${API_BASE}/api/game/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, action, hotspot_id: hotspotId }),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  sessionId = data.session_id;
  writeSessionId(sessionId);
  return data;
}

async function loadEvidence() {
  if (!sessionId || typeof fetch !== "function") return;
  const response = await fetch(
    `${API_BASE}/api/game/evidence?session_id=${encodeURIComponent(sessionId)}`,
  );
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  renderEvidence(await response.json());
}

function renderEvidence(evidence) {
  if (!evidenceList || !evidenceEmpty) return;
  evidenceList.replaceChildren();
  evidenceEmpty.hidden = evidence.length > 0;
  for (const item of evidence) {
    const card = document.createElement("li");
    card.className = "evidence-card";
    const title = document.createElement("h3");
    title.textContent = item.title;
    const summary = document.createElement("p");
    summary.textContent = item.summary;
    const actions = document.createElement("div");
    actions.className = "evidence-actions";
    for (const characterId of Object.keys(CHARACTERS)) {
      const present = document.createElement("button");
      present.type = "button";
      present.textContent = item.presented_to.includes(characterId)
        ? `已向 ${CHARACTERS[characterId].name} 出示`
        : `向 ${CHARACTERS[characterId].name} 出示`;
      present.disabled = item.presented_to.includes(characterId);
      present.addEventListener("click", async () => {
        try {
          const response = await fetch(`${API_BASE}/api/game/present`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: sessionId,
              character_id: characterId,
              evidence_id: item.evidence_id,
            }),
          });
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const result = await response.json();
          status.textContent = `已向 ${CHARACTERS[result.character_id].name} 出示证据。`;
          await loadEvidence();
        } catch (_error) {
          status.textContent = "出示证据失败，请重试。";
        }
      });
      actions.appendChild(present);
    }
    card.append(title, summary, actions);
    evidenceList.appendChild(card);
  }
}

function applyInvestigationState(state) {
  for (const button of investigationButtons) {
    const hotspotState = state.hotspots?.[button.dataset.hotspotId];
    button.classList.toggle("is-completed", hotspotState === "completed");
  }
  if (claudePrivateInterview) {
    claudePrivateInterview.hidden = !state.private_interview_challenges?.claude;
  }
  if (switchButtons.claude) {
    switchButtons.claude.hidden = !state.available_characters?.includes("claude");
  }
  if (doubaoPrivateInterview) {
    doubaoPrivateInterview.hidden = !state.private_interview_challenges?.doubao;
  }
  if (gptPrivateInterview) {
    gptPrivateInterview.hidden = !state.private_interview_challenges?.chatgpt;
  }
  if (switchButtons.chatgpt) {
    switchButtons.chatgpt.hidden = !state.available_characters?.includes("chatgpt");
  }
  if (switchButtons.doubao) {
    switchButtons.doubao.hidden = !state.available_characters?.includes("doubao");
  }
}

if (gptPrivateSubmit && gptPrivateInterview) {
  gptPrivateSubmit.addEventListener("click", async () => {
    if (!sessionId) return;
    try {
      const response = await fetch(`${API_BASE}/api/game/private-interview/challenge`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, character_id: "chatgpt", claim_ids: [], evidence_ids: ["EV06_SESSION_REPLAY_MARKER"] }) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      status.textContent = result.outcome === "UNLOCKED" ? "GPT 承认：她在替你安排调查优先级。已获得当前玩家身份记录。" : "这项证据尚未形成可追问的遗漏。";
      if (result.outcome === "UNLOCKED") { await loadInvestigationState(); loadEvidence().catch(() => {}); }
    } catch (_error) { status.textContent = "私审提交失败，请重试。"; }
  });
}

if (doubaoPrivateSubmit && doubaoPrivateInterview) {
  doubaoPrivateSubmit.addEventListener("click", async () => {
    const observation = doubaoPrivateInterview.querySelector("input[name='doubao-observation']:checked")?.value;
    if (!sessionId || !observation) return;
    try {
      const response = await fetch(`${API_BASE}/api/game/private-interview/challenge`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, character_id: "doubao", claim_ids: ["CL_DB_01"], evidence_ids: [observation] }) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      status.textContent = result.outcome === "UNLOCKED" ? "豆包私审完成：她看到的是系统文字，不是 GPT 本人。" : "这仍是解释，不是豆包实际观察到的事实。";
      if (result.outcome === "UNLOCKED") { await loadInvestigationState(); loadEvidence().catch(() => {}); }
    } catch (_error) { status.textContent = "私审提交失败，请重试。"; }
  });
}

async function loadInvestigationState() {
  if (!sessionId || typeof fetch !== "function") return;
  const response = await fetch(
    `${API_BASE}/api/game/state?session_id=${encodeURIComponent(sessionId)}`,
  );
  if (response.ok) applyInvestigationState(await response.json());
}

for (const button of investigationButtons) {
  button.addEventListener("click", async () => {
    const isPaperHotspot = button.dataset.hotspotId === "CH1_NOTE_01";
    if (isPaperHotspot) paperPanel.hidden = false;
    try {
      const data = await sendInvestigationAction("INSPECT_HOTSPOT", button.dataset.hotspotId);
      applyInvestigationState(data.state);
      applyPresentation(data.presentation);
      loadEvidence().catch(() => {});
      status.textContent = data.outcome === "ALREADY_COMPLETED" ? "这里已经调查完毕。" : "已调查。";
    } catch (_error) {
      status.textContent = API_BASE
        ? "调查服务未连接：请先启动后端，或通过 http://127.0.0.1:8000/frontend/index.html 打开。"
        : "调查失败，请重试。";
    }
  });
}

if (evidenceToggle) {
  evidenceToggle.addEventListener("click", async () => {
    if (evidencePanel.hidden) {
      try {
        await loadEvidence();
        evidencePanel.hidden = false;
        evidenceToggle.textContent = "收起证据";
      } catch (_error) {
        status.textContent = "证据加载失败。";
      }
    } else {
      evidencePanel.hidden = true;
      evidenceToggle.textContent = "证据";
    }
  });
}

paperClose?.addEventListener("click", () => { paperPanel.hidden = true; });

if (rubbingSurface && rubbingCanvas && typeof document.createElement === "function") {
  const GRID_COLUMNS = 28;
  const GRID_ROWS = 15;
  const COMPLETE_COVERAGE = 0.38;
  const graphiteCanvas = document.createElement("canvas");
  const context = rubbingCanvas.getContext?.("2d");
  const graphiteContext = graphiteCanvas.getContext?.("2d");
  const coveredCells = new Set();
  let width = 0;
  let height = 0;
  let pixelRatio = 1;
  let previousPoint = null;
  let submitted = false;

  function drawPaperTexture(target) {
    target.fillStyle = "#e7dfce";
    target.fillRect(0, 0, width, height);
    target.globalCompositeOperation = "multiply";
    for (let index = 0; index < width * height / 170; index += 1) {
      const shade = 184 + ((index * 37) % 34);
      target.fillStyle = `rgba(${shade}, ${shade - 8}, ${shade - 20}, .12)`;
      target.fillRect((index * 71) % width, (index * 43) % height, 1, 1);
    }
    target.globalCompositeOperation = "source-over";
  }

  function drawImprint(target, alpha = 1) {
    const centerX = width * 0.5;
    const centerY = height * 0.5;
    target.save();
    target.translate(centerX, centerY);
    target.rotate(-0.045);
    target.textAlign = "center";
    target.textBaseline = "middle";
    target.font = "700 30px Georgia, serif";
    target.fillStyle = `rgba(67, 49, 36, ${0.23 * alpha})`;
    target.fillText("LOG ACCESS", 2, -13);
    target.font = "600 18px ui-monospace, Consolas, monospace";
    target.fillText("R7K4-19", 2, 24);
    target.fillStyle = `rgba(248, 240, 224, ${0.84 * alpha})`;
    target.font = "700 30px Georgia, serif";
    target.fillText("LOG ACCESS", 0, -15);
    target.font = "600 18px ui-monospace, Consolas, monospace";
    target.fillText("R7K4-19", 0, 22);
    target.restore();
  }

  function liftImprint() {
    graphiteContext.save();
    graphiteContext.globalCompositeOperation = "destination-out";
    drawImprint(graphiteContext, 0.93);
    graphiteContext.restore();
  }

  function renderPaper() {
    context.save();
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    drawPaperTexture(context);
    context.drawImage(graphiteCanvas, 0, 0, width, height);
    drawImprint(context, Math.max(0.12, coveredCells.size / (GRID_COLUMNS * GRID_ROWS)));
    context.restore();
  }

  function resizePaper() {
    const bounds = rubbingSurface.getBoundingClientRect();
    const nextWidth = Math.max(1, Math.round(bounds.width));
    const nextHeight = Math.max(1, Math.round(bounds.height));
    if (nextWidth === width && nextHeight === height) return;
    width = nextWidth;
    height = nextHeight;
    pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    rubbingCanvas.width = width * pixelRatio;
    rubbingCanvas.height = height * pixelRatio;
    graphiteCanvas.width = width * pixelRatio;
    graphiteCanvas.height = height * pixelRatio;
    graphiteContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    liftImprint();
    renderPaper();
  }

  function markCoverage(from, to) {
    const distance = Math.max(1, Math.hypot(to.x - from.x, to.y - from.y));
    for (let step = 0; step <= distance; step += 7) {
      const progress = step / distance;
      const x = from.x + (to.x - from.x) * progress;
      const y = from.y + (to.y - from.y) * progress;
      const column = Math.min(GRID_COLUMNS - 1, Math.max(0, Math.floor(x / width * GRID_COLUMNS)));
      const row = Math.min(GRID_ROWS - 1, Math.max(0, Math.floor(y / height * GRID_ROWS)));
      coveredCells.add(`${column}:${row}`);
    }
  }

  function depositGraphite(from, to) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const length = Math.max(1, Math.hypot(dx, dy));
    const normalX = -dy / length;
    const normalY = dx / length;
    graphiteContext.save();
    graphiteContext.lineCap = "round";
    for (let line = -2; line <= 2; line += 1) {
      const offset = line * 1.8 + (Math.random() - .5) * 1.2;
      graphiteContext.globalAlpha = 0.12 + Math.random() * 0.08;
      graphiteContext.strokeStyle = "#373239";
      graphiteContext.lineWidth = 1.65 + Math.random() * .9;
      graphiteContext.beginPath();
      graphiteContext.moveTo(from.x + normalX * offset, from.y + normalY * offset);
      graphiteContext.lineTo(to.x + normalX * offset, to.y + normalY * offset);
      graphiteContext.stroke();
    }
    for (let particle = 0; particle < Math.ceil(length / 5); particle += 1) {
      const progress = Math.random();
      const spread = (Math.random() - .5) * 11;
      graphiteContext.globalAlpha = 0.08 + Math.random() * 0.13;
      graphiteContext.fillStyle = "#2d2930";
      graphiteContext.beginPath();
      graphiteContext.arc(from.x + dx * progress + normalX * spread, from.y + dy * progress + normalY * spread, .35 + Math.random() * 1.1, 0, Math.PI * 2);
      graphiteContext.fill();
    }
    graphiteContext.restore();
    liftImprint();
  }

  async function completeRubbing() {
    submitted = true;
    graphiteContext.save();
    graphiteContext.fillStyle = "rgba(53, 48, 56, .12)";
    graphiteContext.fillRect(0, 0, width, height);
    graphiteContext.restore();
    liftImprint();
    renderPaper();
    rubbingSurface.classList.add("is-revealed");
    try {
      const data = await sendInvestigationAction("PAPER_RUBBING_COMPLETE", "CH1_NOTE_01");
      applyInvestigationState(data.state);
      applyPresentation(data.presentation);
      status.textContent = data.evidence_id ? "发现了一条重要线索。" : "纸张已调查。";
    } catch (_error) {
      submitted = false;
      status.textContent = "涂画提交失败，请重试。";
    }
  }

  rubbingSurface.addEventListener("pointerenter", resizePaper);
  rubbingSurface.addEventListener("pointerleave", () => { previousPoint = null; });
  rubbingSurface.addEventListener("pointermove", (event) => {
    if (submitted) return;
    resizePaper();
    const bounds = rubbingSurface.getBoundingClientRect();
    const point = { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
    if (previousPoint) {
      depositGraphite(previousPoint, point);
      markCoverage(previousPoint, point);
      renderPaper();
      if (coveredCells.size >= GRID_COLUMNS * GRID_ROWS * COMPLETE_COVERAGE) completeRubbing();
    }
    previousPoint = point;
  });
}

function setWaiting(waiting) {
  input.disabled = waiting;
  sendButton.disabled = waiting;
  sendButton.textContent = waiting ? "思考中…" : "发送";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();

  if (!message) {
    status.textContent = "请先输入一句话。";
    input.focus();
    return;
  }
  if (message.startsWith("/推理")) {
    const deduction = message.slice(3).trim();
    if (!deduction || !sessionId) {
      status.textContent = "先获得相关证词后再提交推理。";
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/api/game/deduction`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, message: deduction }) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      status.textContent = result.outcome === "ACCEPTED" ? "推理成立，调查状态已更新。" : "这条推理暂时无法成立。";
      input.value = "";
      loadInvestigationState().catch(() => {});
      loadEvidence().catch(() => {});
    } catch (_error) { status.textContent = "推理提交失败，请重试。"; }
    return;
  }

  const submitted = message;
  input.value = "";
  status.textContent = "已发送；正在等待角色回应…";
  setWaiting(true);

  try {
    const data = await sendMessage(submitted);
    // TV-16: story directives from a committed event (e.g. SHOW_CHARACTER
    // claude) take precedence over who merely speaks this turn (docs/03
    // §13.6, §44.1).
    const presentedCharacter = applyPresentation(data.presentation);
    // The dialogue box always names the actual speaker.
    setSpeaker(data.character_id);
    // If no story directive set the stage, show the speaker (docs/01 §10.1).
    if (
      presentedCharacter === null &&
      characterSprite.dataset.character !== data.character_id
    ) {
      setCharacter(data.character_id);
    }
    // Model-driven emotion + animation (docs/02 §7: 切换表情 / 播放动画).
    window.galPresentation.apply({
      character: characterSprite.dataset.character,
      expression: data.emotion,
    });
    window.galPresentation.apply({
      character: characterSprite.dataset.character,
      animation: data.animation,
    });
    dialogueText.textContent = data.dialogue;
    status.textContent = data.claim_refs?.length
      ? "已收到角色回应；关键证词已记录。"
      : "已收到角色回应。";
    if ((data.presentation || []).some((directive) => directive.startsWith("SHOW_CHARACTER"))) {
      loadInvestigationState().catch(() => {});
    }
  } catch (error) {
    status.textContent = "发送失败，请重试。";
    input.value = submitted; // restore the text so the player can retry
  } finally {
    setWaiting(false);
    input.focus();
  }
});

if (deductionForm && deductionInput) {
  deductionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = deductionInput.value.trim();
    if (!message || !sessionId) {
      status.textContent = "先获得相关证词后再提交推理。";
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/api/game/deduction`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      if (result.outcome === "ACCEPTED") {
        deductionInput.value = "";
        status.textContent = result.id === "INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR"
          ? "推理成立：当前 DeepSeek 不是 03:17 的执行者；GPT 已带着调查摘要加入。"
          : "推理成立：Claude 的信息来源存在断层，已解锁私审挑战。";
        loadInvestigationState().catch(() => {});
        loadEvidence().catch(() => {});
      } else if (result.outcome === "BLOCKED") {
        status.textContent = "推理还缺少关键证词或证据。";
      } else {
        status.textContent = "暂时无法确认这条推理；请换一种更具体的说法。";
      }
    } catch (_error) {
      status.textContent = "推理提交失败，请重试。";
    }
  });
}

if (claudePrivateSubmit && claudePrivateInterview) {
  claudePrivateSubmit.addEventListener("click", async () => {
    if (!sessionId) return;
    const selected = Array.from(
      claudePrivateInterview.querySelectorAll("input[name='claude-claim']:checked"),
      (input) => input.value,
    );
    try {
      const response = await fetch(`${API_BASE}/api/game/private-interview/challenge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          character_id: "claude",
          claim_ids: selected,
          evidence_ids: [],
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      if (result.outcome === "UNLOCKED") {
        status.textContent = "Claude 私审完成：获得了 03:17 执行者残片。";
        await loadInvestigationState();
        loadEvidence().catch(() => {});
      } else {
        status.textContent = "这两条证词还不足以构成完整的信息断层。";
      }
    } catch (_error) {
      status.textContent = "私审提交失败，请重试。";
    }
  });
}

// TV-17: the active opening line (docs/01 §4) — spoken by the backend without
// player input. On load the frontend asks for it once; the backend is
// idempotent, so a restored session returns an empty dialogue and nothing is
// re-rendered. The static line in index.html stays as a no-backend placeholder.
async function openOpening() {
  if (typeof fetch !== "function") return; // DOM-stub tests have no fetch
  try {
    const response = await fetch(`${API_BASE}/api/chat/opening`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!response.ok) return;
    const data = await response.json();
    sessionId = data.session_id;
    writeSessionId(sessionId);
    await loadInvestigationState();
    if (!data.dialogue) return; // already opened: keep the current stage
    applyPresentation(data.presentation);
    setSpeaker(data.character_id);
    setCharacter(data.character_id);
    window.galPresentation.apply({
      character: characterSprite.dataset.character,
      expression: data.emotion,
    });
    window.galPresentation.apply({
      character: characterSprite.dataset.character,
      animation: data.animation,
    });
    dialogueText.textContent = data.dialogue;
  } catch (_error) {
    // No backend yet: the static opening line in index.html stays in place.
  }
}

openOpening();

if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
  const opening = dialogueText.textContent.trim();
  characterSprite.classList.add("is-opening");
  window.requestAnimationFrame(() => {
    let index = 0;
    dialogueText.textContent = "";
    const timer = window.setInterval(() => {
      dialogueText.textContent += opening[index] || "";
      index += 1;
      if (index >= opening.length) window.clearInterval(timer);
    }, 34);
  });
}
