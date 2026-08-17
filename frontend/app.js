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
const switchButtons = {
  deepseek: document.querySelector("#switch-deepseek"),
  claude: document.querySelector("#switch-claude"),
};

const investigationButtons =
  typeof document.querySelectorAll === "function"
    ? document.querySelectorAll("[data-hotspot-id]")
    : [];
const paperPanel = document.querySelector("#paper-panel");
const paperClose = document.querySelector("#paper-close");
const rubbingSurface = document.querySelector("#rubbing-surface");

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

function applyInvestigationState(state) {
  for (const button of investigationButtons) {
    const hotspotState = state.hotspots?.[button.dataset.hotspotId];
    button.classList.toggle("is-completed", hotspotState === "completed");
  }
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
    try {
      const data = await sendInvestigationAction("INSPECT_HOTSPOT", button.dataset.hotspotId);
      applyInvestigationState(data.state);
      if (button.dataset.hotspotId === "CH1_NOTE_01") paperPanel.hidden = false;
      status.textContent = data.outcome === "ALREADY_COMPLETED" ? "这里已经调查完毕。" : "已调查。";
    } catch (_error) {
      status.textContent = "调查失败，请重试。";
    }
  });
}

paperClose?.addEventListener("click", () => { paperPanel.hidden = true; });

if (rubbingSurface) {
  let coveredPoints = 0;
  let submitted = false;
  rubbingSurface.addEventListener("pointermove", async () => {
    if (submitted) return;
    coveredPoints += 1;
    if (coveredPoints < 30) return;
    submitted = true;
    rubbingSurface.classList.add("is-revealed");
    try {
      const data = await sendInvestigationAction("PAPER_RUBBING_COMPLETE", "CH1_NOTE_01");
      applyInvestigationState(data.state);
      status.textContent = data.evidence_id ? "发现了一条重要线索。" : "纸张已调查。";
    } catch (_error) {
      submitted = false;
      status.textContent = "涂画提交失败，请重试。";
    }
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
    status.textContent = "已收到角色回应。";
  } catch (error) {
    status.textContent = "发送失败，请重试。";
    input.value = submitted; // restore the text so the player can retry
  } finally {
    setWaiting(false);
    input.focus();
  }
});

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
