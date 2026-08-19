const form = document.querySelector("#player-form");
const input = document.querySelector("#player-message");
const dialogueText = document.querySelector("#dialogue-text");
const status = document.querySelector("#form-status");
const characterSprite = document.querySelector("#character-sprite");
const characterName = document.querySelector("#character-name");
const sendButton = form.querySelector("button[type='submit']");
const gameShell = document.querySelector(".game-shell");
const openingOverlay = document.querySelector("#opening-overlay");
const openingSpeaker = document.querySelector("#opening-speaker");
const openingText = document.querySelector("#opening-text");
const skipOpeningButton = document.querySelector("#skip-opening");

// TV-16: backend-selected speaker display plus History/Evidence views.
const historyToggle = document.querySelector("#history-toggle");
const historyPanel = document.querySelector("#history-panel");
const historyList = document.querySelector("#history-list");
const evidenceToggle = document.querySelector("#evidence-toggle");
const evidencePanel = document.querySelector("#evidence-panel");
const evidenceList = document.querySelector("#evidence-list");
const evidenceEmpty = document.querySelector("#evidence-empty");
const gameModal = document.querySelector("#game-modal");
const modalTitle = document.querySelector("#modal-title");
const modalClose = document.querySelector("#modal-close");
const investigationPanel = document.querySelector("#investigation-panel");
const investigationPreview = document.querySelector("#investigation-preview");
const investigationProgress = document.querySelector("#investigation-progress");
const investigationConfirm = document.querySelector("#investigation-confirm");

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
let paperInvestigationPromise = null;
let latestInvestigationState = null;
let selectedHotspotId = null;

// TV-16: per-character display (docs/01 §10.1-10.2).
const CHARACTERS = {
  deepseek: {
    name: "DeepSeek",
    sprite: "../char/deepseek/pic/deepseek_main.png",
  },
  claude: {
    name: "Claude",
    sprite: "./public/characters/claude-main.png",
  },
  chatgpt: {
    name: "ChatGPT",
    sprite: "./public/characters/claude-placeholder.svg",
  },
  doubao: {
    name: "豆包",
    sprite: "./public/characters/claude-placeholder.svg",
  },
  // A script line narrated by the system (e.g. the 03:17 warning) has no
  // sprite on stage; only the speaker label uses this entry.
  system: {
    name: "系统",
  },
};


// CharacterStage — the multi-character stage (docs/12 §10, §39 Task 2).
// Auto-positioning places visible sprites at (i+1)/(n+1); an explicit slot
// overrides the auto position (docs/12 §10.1: explicit slot > manual offset >
// auto). The Frontend only executes registered Presentation Actions — it never
// decides who is on stage by itself.
const SLOT_PCT = {
  LEFT: 18,
  CENTER_LEFT: 36,
  CENTER: 50,
  CENTER_RIGHT: 64,
  RIGHT: 82,
};
const MIN_SPRITE_GAP_PCT = 3;

class CharacterStage {
  constructor(root, characters) {
    this.root = root;          // #character-stage (null in hand-written DOM stubs)
    this.characters = characters;
    this.sprites = new Map();  // character_id -> sprite element
    this.slots = new Map();    // character_id -> explicit slot name
    this.offsets = new Map();  // character_id -> { scale, offsetX, offsetY }
    this.focal = null;         // the character the presentation last focused
  }

  // Ensure a character's sprite exists on the stage. DeepSeek is the static
  // #character-sprite anchor (tv02 keeps driving it); every other character
  // gets a dynamically created figure (docs/12 §39 Task 2).
  ensure(characterId) {
    if (characterId === "system" || !this.characters[characterId]) return null;
    if (this.sprites.has(characterId)) return this.sprites.get(characterId);
    let sprite = null;
    if (characterId === "deepseek" && characterSprite) {
      sprite = characterSprite;
    } else if (
      typeof document !== "undefined" &&
      typeof document.createElement === "function"
    ) {
      sprite = document.createElement("figure");
      sprite.className = "character-sprite is-hidden";
      sprite.dataset.character = characterId;
      sprite.dataset.emotion = "neutral";
      const image = document.createElement("img");
      image.alt = `${this.characters[characterId].name} 的角色立绘`;
      image.src = this.characters[characterId].sprite;
      sprite.appendChild(image);
      if (this.root) this.root.appendChild(sprite);
    }
    if (sprite) {
      this.sprites.set(characterId, sprite);
      this.layout();
    }
    return sprite;
  }

  show(characterId, { emotion, slot, animation } = {}) {
    if (characterId === "system" || !this.characters[characterId]) return null;
    const sprite = this.ensure(characterId);
    if (!sprite) return null;
    sprite.classList.remove("is-hidden");
    this.focal = characterId;
    if (slot) this.slots.set(characterId, slot);
    if (emotion) this.setEmotion(characterId, emotion);
    if (animation && animation !== "none") this.animate(characterId, animation);
    this.layout();
    return sprite;
  }

  hide(characterId) {
    if (characterId === "system") return;
    const sprite = this.sprites.get(characterId);
    if (!sprite) return;
    if (characterId === "deepseek") {
      // The static anchor stays in the DOM; visibility drops its click area.
      sprite.classList.add("is-hidden");
    } else {
      sprite.remove?.();
      this.sprites.delete(characterId);
      this.slots.delete(characterId);
      this.offsets.delete(characterId);
    }
    this.layout();
  }

  setEmotion(characterId, emotion) {
    if (characterId === "system" || !emotion) return;
    const sprite = this.ensure(characterId);
    if (!sprite) return;
    sprite.dataset.emotion = emotion;
    sprite.dataset.expression = emotion;
  }

  animate(characterId, animation) {
    if (characterId === "system" || !animation || animation === "none") return;
    const sprite = this.sprites.get(characterId);
    if (!sprite) return;
    const animationClass = animationClasses[animation];
    if (!animationClass) {
      console.warn(`unknown animation: ${animation}`);
      return;
    }
    sprite.classList.remove(animationClass);
    void sprite.offsetWidth;
    sprite.classList.add(animationClass);
    sprite.addEventListener(
      "animationend",
      () => {
        sprite.classList.remove(animationClass);
        if (animation === "fade_out") sprite.classList.add("is-hidden");
      },
      { once: true },
    );
  }

  // Highlights the speaking sprite; never changes who is on stage.
  setSpeaking(characterId) {
    for (const [id, sprite] of this.sprites) {
      sprite.classList.toggle("is-speaking", id === characterId);
    }
  }

  setInputLock(locked) {
    if (input) input.disabled = locked;
    if (sendButton) sendButton.disabled = locked;
  }

  setBackground(_background, fade) {
    // v1 ships one scene painting (styles.css .scene-background); a scene id
    // change is presented as a fade cue, never an art swap (docs/12 §42).
    if (!gameShell?.classList) return;
    if (fade) {
      gameShell.classList.remove("is-scene-fading");
      void gameShell.offsetWidth;
      gameShell.classList.add("is-scene-fading");
    }
  }

  screenShake(intensity) {
    if (!gameShell?.classList) return;
    gameShell.classList.remove("is-screen-shaking");
    void gameShell.offsetWidth;
    gameShell.dataset.effectIntensity = intensity || "medium";
    gameShell.classList.add("is-screen-shaking");
  }

  screenGlitch(intensity) {
    if (!gameShell?.classList) return;
    gameShell.classList.remove("is-glitching");
    void gameShell.offsetWidth;
    gameShell.dataset.effectIntensity = intensity || "medium";
    gameShell.classList.add("is-glitching");
  }

  dialogueFocus() {
    const panel = dialogueText?.closest?.(".dialogue-panel");
    if (!panel?.classList) return;
    panel.classList.remove("is-focused");
    void panel.offsetWidth;
    panel.classList.add("is-focused");
  }

  apply(action) {
    if (!action || typeof action !== "object") {
      return { applied: false, reason: "malformed_action" };
    }
    switch (action.type) {
      case "CHARACTER_SHOW":
        this.show(action.character_id, action);
        break;
      case "CHARACTER_HIDE":
        this.hide(action.character_id);
        break;
      case "CHARACTER_EMOTION":
        if (action.slot) this.slots.set(action.character_id, action.slot);
        if (action.scale != null || action.offset_x != null || action.offset_y != null) {
          this.offsets.set(action.character_id, {
            scale: action.scale ?? 1,
            offsetX: action.offset_x ?? 0,
            offsetY: action.offset_y ?? 0,
          });
        }
        this.setEmotion(action.character_id, action.emotion);
        this.layout();
        break;
      case "CHARACTER_ANIMATION":
        this.animate(action.character_id, action.animation);
        break;
      case "BACKGROUND_SET":
        this.setBackground(action.background, false);
        break;
      case "BACKGROUND_FADE":
        this.setBackground(action.background, true);
        break;
      case "SCREEN_SHAKE":
        this.screenShake(action.intensity);
        break;
      case "SCREEN_GLITCH":
        this.screenGlitch(action.intensity);
        break;
      case "DIALOGUE_FOCUS":
        this.dialogueFocus();
        break;
      case "INPUT_LOCK":
        this.setInputLock(true);
        break;
      case "INPUT_UNLOCK":
        this.setInputLock(false);
        break;
      default:
        return { applied: false, reason: "unknown_action" };
    }
    return { applied: true };
  }

  // docs/12 §10: visible sprites get (i+1)/(n+1); a slotted sprite keeps its
  // named spot while the auto sprites yield around it (docs/12 §10.1). The
  // cast shrinks so three or four sprites stay readable.
  layout() {
    if (!this.root) return;
    const visible = [...this.sprites.values()].filter(
      (sprite) => !sprite.classList.contains("is-hidden"),
    );
    const count = visible.length;
    if (count === 0) return;

    const slotted = [];
    const auto = [];
    for (const sprite of visible) {
      const id = sprite.dataset.character;
      const slot = this.slots.get(id);
      if (slot && SLOT_PCT[slot] != null) {
        slotted.push({ id, pct: SLOT_PCT[slot] });
      } else {
        auto.push({ id, pct: null });
      }
    }
    const occupied = slotted.map((entry) => entry.pct).sort((a, b) => a - b);
    const clear = (pct) =>
      occupied.every((other) => Math.abs(pct - other) >= MIN_SPRITE_GAP_PCT);
    auto.forEach((entry, index) => {
      const ideal = ((index + 1) / (auto.length + 1)) * 100;
      let pct = ideal;
      if (!clear(pct)) {
        let left = ideal;
        let right = ideal;
        while (!clear(left) && left > 6) left -= MIN_SPRITE_GAP_PCT;
        while (!clear(right) && right < 94) right += MIN_SPRITE_GAP_PCT;
        const leftClear = clear(left);
        const rightClear = clear(right);
        pct = leftClear && rightClear
          ? (Math.abs(left - ideal) <= Math.abs(right - ideal) ? left : right)
          : leftClear ? left : right;
      }
      entry.pct = Math.max(6, Math.min(94, pct));
      occupied.push(entry.pct);
      occupied.sort((a, b) => a - b);
    });

    const resolved = new Map();
    for (const entry of [...slotted, ...auto]) resolved.set(entry.id, entry.pct);

    const stageScale = count >= 4 ? 0.72 : count === 3 ? 0.82 : count === 2 ? 0.94 : 1;
    for (const sprite of visible) {
      const id = sprite.dataset.character;
      const offset = this.offsets.get(id);
      sprite.style.left = `${resolved.get(id)}%`;
      sprite.style.setProperty("--scale", stageScale * (offset?.scale ?? 1));
      sprite.style.setProperty("--offset-x", `${offset?.offsetX ?? 0}px`);
      sprite.style.setProperty("--offset-y", `${offset?.offsetY ?? 0}px`);
    }
  }

  // docs/12 §39 Task 1: the Frontend never infers who is on stage; it applies
  // the authoritative presentation_state from GET /api/game/state.
  applyState(presentationState) {
    if (!presentationState) return;
    const characters = Array.isArray(presentationState.characters)
      ? presentationState.characters
      : [];
    const visibleIds = new Set(
      characters.filter((entry) => entry.visible).map((entry) => entry.character_id),
    );
    for (const [id] of this.sprites) {
      if (id === "deepseek") continue; // the anchor never leaves the stage
      if (!visibleIds.has(id)) this.hide(id);
    }
    for (const entry of characters) {
      if (!entry.visible) continue;
      const sprite = this.show(entry.character_id, {
        emotion: entry.emotion,
        slot: entry.slot,
      });
      if (!sprite) continue;
      sprite.classList.remove("is-hidden");
    }
    if (presentationState.input_mode === "locked") {
      this.setInputLock(true);
    }
    this.layout();
  }
}

const stage = new CharacterStage(document.querySelector("#character-stage"), CHARACTERS);

if (typeof window !== "undefined") {
  window.galStage = {
    apply: (action) => stage.apply(action),
    applyState: (state) => stage.applyState(state),
  };
}


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

// Opening presentation is intentionally local and deterministic: it controls
// only what the player sees before input is unlocked, never narrative facts.
const OPENING_SEQUENCE = [
  { phase: "boot", text: "……", duration: 1200 },
  { phase: "wake_text", text: "头……好痛。", duration: 1800 },
  { phase: "room_reveal", text: "……这里是哪？", duration: 2500 },
  { phase: "restraint_reveal", text: "手腕……动不了。", duration: 1500 },
  { phase: "voice_before_sprite", speaker: "？？？", text: "……你醒了？\n先别乱动。", duration: 2000 },
  { phase: "deepseek_reveal", speaker: "DeepSeek", duration: 2500 },
];

let presentationMode = "opening";
let openingRunId = 0;
let openingLinePromise = null;

function openingStorageKey(id) {
  return id ? `gal_opening_completed:${id}` : null;
}

function openingWasCompleted(id) {
  const key = openingStorageKey(id);
  if (!key || typeof localStorage === "undefined") return false;
  try {
    return localStorage.getItem(key) === "true";
  } catch (_error) {
    return false;
  }
}

function markOpeningCompleted(id) {
  const key = openingStorageKey(id);
  if (!key || typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(key, "true");
  } catch (_error) {
    // Presentation persistence is best-effort; a storage failure must never
    // lock the player out of the game.
  }
}

function isInteractive() {
  return presentationMode === "interactive";
}

function setPresentationMode(mode) {
  presentationMode = mode;
  if (gameShell) {
    gameShell.dataset.presentationMode = mode;
    gameShell.classList.toggle("is-opening", mode === "opening");
  }
  const locked = mode !== "interactive";
  input.disabled = locked;
  sendButton.disabled = locked;
}

function renderOpeningStep({ phase, speaker = "", text = "" }) {
  if (gameShell) gameShell.dataset.openingPhase = phase;
  if (openingSpeaker) openingSpeaker.textContent = speaker;
  if (openingText && text) openingText.textContent = text;
}

function waitForOpening(duration, runId) {
  return new Promise((resolve) => {
    const schedule = typeof window !== "undefined" && window.setTimeout
      ? window.setTimeout.bind(window)
      : setTimeout;
    schedule(() => resolve(runId === openingRunId), duration);
  });
}

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
  strong_shake: "is-shaking",
  small_jump: "is-small-jumping",
  slide_in_left: "is-sliding-in-left",
  slide_in_right: "is-sliding-in-right",
};

const expressionNames = new Set([
  "normal",
  "alert",
  "neutral",
  "happy",
  "annoyed",
  "angry",
  "embarrassed",
  "serious",
  "surprised",
]);

function replayAnimation(sprite, className, afterAnimation) {
  sprite.classList.remove(className);
  void sprite.offsetWidth;
  sprite.classList.add(className);
  sprite.addEventListener(
    "animationend",
    () => {
      sprite.classList.remove(className);
      afterAnimation?.();
    },
    { once: true },
  );
}

function applyPresentationDirective({ character, animation, expression } = {}) {
  if (character === "system" || !CHARACTERS[character]) {
    return { applied: false, reason: "unknown_character" };
  }

  if (expression !== undefined && !expressionNames.has(expression)) {
    return { applied: false, reason: "unknown_expression" };
  }

  const sprite = stage.ensure(character);
  if (!sprite) {
    return { applied: false, reason: "unknown_character" };
  }

  if (expression !== undefined) {
    sprite.dataset.expression = expression;
    sprite.dataset.emotion = expression;
  }

  if (animation !== undefined && animation !== "none") {
    const animationClass = animationClasses[animation];
    if (!animationClass) {
      return { applied: false, reason: "unknown_animation" };
    }
    if (animation === "fade_in") {
      sprite.classList.remove("is-hidden");
    }
    replayAnimation(sprite, animationClass, () => {
      if (animation === "fade_out") {
        sprite.classList.add("is-hidden");
      }
    });
  }

  return { applied: true };
}

if (typeof window !== "undefined") {
  window.galPresentation = { apply: applyPresentationDirective };
}

// TV-16: switch which character is displayed on stage (docs/01 §10.2). With the
// stage this means "ensure that character's sprite is on stage" (docs/12 §39
// Task 2); fadeIn also plays the allowed fade_in animation (docs/03 §44.1).
function setCharacter(characterId, { fadeIn = false } = {}) {
  if (characterId === "system" || !CHARACTERS[characterId]) return;
  const sprite = stage.show(characterId);
  if (!sprite) return;
  if (fadeIn) stage.animate(characterId, "fade_in");
}

// TV-16: the dialogue box names whoever actually spoke (docs/01 §7 当前发言
// 角色正确), independent of who the stage sprite shows.
function setSpeaker(characterId) {
  const character = CHARACTERS[characterId];
  if (!character) return;
  characterName.textContent = character.name;
  stage.setSpeaking(characterId);
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
      stage.apply({ type: "CHARACTER_SHOW", character_id: target, animation: "fade_in" });
    } else if (kind === "HIDE_CHARACTER") {
      stage.apply({ type: "CHARACTER_HIDE", character_id: target });
    } else if (kind === "PLAY_ANIMATION" && target) {
      stage.apply({
        type: "CHARACTER_ANIMATION",
        character_id: presentedCharacter || stage.focal,
        animation: target,
      });
    }
    // FADE / FADE_IN / FADE_OUT / PLAY_EFFECT: presentation details the
    // current fixture does not need to render.
  }
  return presentedCharacter;
}

// docs/12 §13: the structured channel. Registered actions are executed by the
// CharacterStage; anything the stage rejects is logged (never silently run).
function applyPresentationActions(actions) {
  let presentedCharacter = null;
  for (const action of actions || []) {
    if (!action || typeof action !== "object") continue;
    const result = stage.apply(action);
    if (action.type === "CHARACTER_SHOW") presentedCharacter = action.character_id;
    if (result && !result.applied) {
      console.warn(`unknown presentation action: ${JSON.stringify(action)}`);
    }
  }
  return presentedCharacter;
}

// History and Evidence share one in-game modal. They use the existing backend
// read APIs; opening or closing the window never changes game state.
async function loadHistory() {
  if (!sessionId) {
    renderHistory([]);
    return;
  }
  const response = await fetch(
    `${API_BASE}/api/chat/history?session_id=${encodeURIComponent(sessionId)}`,
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
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

function closeGameModal() {
  if (!gameModal) return;
  gameModal.hidden = true;
  if (historyPanel) historyPanel.hidden = true;
  if (evidencePanel) evidencePanel.hidden = true;
  if (investigationPanel) investigationPanel.hidden = true;
  selectedHotspotId = null;
}

async function openGameModal(kind, { highlightEvidenceId = null } = {}) {
  if (!gameModal || !modalTitle) return;
  try {
    if (kind === "history") {
      await loadHistory();
      modalTitle.textContent = "对话历史";
      historyPanel.hidden = false;
      evidencePanel.hidden = true;
      if (investigationPanel) investigationPanel.hidden = true;
    } else {
      await loadEvidence(highlightEvidenceId);
      modalTitle.textContent = "证据";
      evidencePanel.hidden = false;
      historyPanel.hidden = true;
      if (investigationPanel) investigationPanel.hidden = true;
    }
    gameModal.hidden = false;
    modalClose?.focus?.();
  } catch (_error) {
    status.textContent = kind === "history" ? "历史加载失败。" : "证据加载失败。";
  }
}

historyToggle?.addEventListener("click", () => openGameModal("history"));
evidenceToggle?.addEventListener("click", () => {
  if (!isInteractive()) return undefined;
  return openGameModal("evidence");
});
modalClose?.addEventListener("click", closeGameModal);
gameModal?.addEventListener("click", (event) => {
  if (event.target === gameModal) closeGameModal();
});
if (typeof document.addEventListener === "function") {
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && gameModal && !gameModal.hidden) closeGameModal();
  });
}

async function sendMessage(message) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
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
  if (!response.ok) {
    let detail = `调查请求失败（HTTP ${response.status}）`;
    try {
      const errorBody = await response.json();
      if (errorBody.detail) detail = errorBody.detail;
    } catch (_error) {
      // Keep the HTTP fallback when the server did not return JSON.
    }
    throw new Error(detail);
  }
  const data = await response.json();
  sessionId = data.session_id;
  writeSessionId(sessionId);
  return data;
}

function investigationErrorMessage(error) {
  const detail = error?.message || "";
  if (detail.includes("before the 03:17 incident")) {
    return "这里暂时无法调查。先检查房间里已经出现的异常。";
  }
  if (detail.includes("not available in the current scene")) {
    return "这个调查点不在当前场景中。";
  }
  if (detail.includes("unavailable in Bad End") || detail.includes("unavailable after To Be Continued")) {
    return "当前剧情阶段已经无法继续调查。";
  }
  if (detail === "Failed to fetch" || detail.includes("NetworkError")) {
    return "无法连接调查服务，请确认后端正在运行后重试。";
  }
  return detail ? `调查暂时无法完成：${detail}` : "调查失败，请重试。";
}

function ensurePaperInvestigation() {
  if (!paperInvestigationPromise) {
    paperInvestigationPromise = sendInvestigationAction(
      "INSPECT_HOTSPOT",
      "CH1_NOTE_01",
    );
  }
  return paperInvestigationPromise;
}

async function loadEvidence(highlightEvidenceId = null) {
  if (!sessionId || typeof fetch !== "function") {
    renderEvidence([], highlightEvidenceId);
    return;
  }
  const response = await fetch(
    `${API_BASE}/api/game/evidence?session_id=${encodeURIComponent(sessionId)}`,
  );
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  renderEvidence(await response.json(), highlightEvidenceId);
}

function renderEvidence(evidence, highlightEvidenceId = null) {
  if (!evidenceList || !evidenceEmpty) return;
  const presentation = latestInvestigationState?.evidence_presentation || {
    unlocked: false,
    character_ids: [],
  };
  const presentableCharacterIds = new Set(presentation.character_ids || []);
  evidenceList.replaceChildren();
  evidenceEmpty.hidden = evidence.length > 0;
  for (const item of evidence) {
    const card = document.createElement("li");
    card.className = "evidence-card";
    if (item.evidence_id === highlightEvidenceId) {
      card.className += " is-highlighted";
    }
    const title = document.createElement("h3");
    title.textContent = item.title;
    const summary = document.createElement("p");
    summary.textContent = item.summary;
    const actions = document.createElement("div");
    actions.className = "evidence-actions";
    for (const characterId of presentableCharacterIds) {
      if (!CHARACTERS[characterId]) continue;
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
    card.append(title, summary);
    if (presentation.unlocked) card.append(actions);
    evidenceList.appendChild(card);
    if (item.evidence_id === highlightEvidenceId) {
      card.scrollIntoView?.({ block: "nearest" });
    }
  }
}

function applyInvestigationState(state) {
  latestInvestigationState = state;
  const hasAuthoredHotspots = Array.isArray(state.available_hotspots);
  const fallbackHotspots = [
    {
      hotspot_id: "CH1_NOTE_01",
      title: "桌上的纸",
      preview: "桌面上压着一张近乎空白的纸，旁边留着一支削尖的铅笔。纸面似乎有很浅的压痕。",
      interaction_type: "paper_rubbing",
    },
  ];
  if (!hasAuthoredHotspots && state.available_characters?.includes("claude")) {
    fallbackHotspots.push(
      {
        hotspot_id: "CH1_TERMINAL_MAIN",
        title: "主终端",
        preview: "终端仍停留在系统日志界面。屏幕有短暂闪烁，最近一次管理员会话值得进一步检查。",
        interaction_type: "inspect",
      },
      {
        hotspot_id: "CH1_C02_DOOR",
        title: "C-02 隔离门",
        preview: "隔离门已经解除锁定，门侧的本地控制器却处于禁用状态。释放记录或许能说明它是如何打开的。",
        interaction_type: "inspect",
      },
      {
        hotspot_id: "CH1_CHARACTER_REGISTRY",
        title: "角色注册表",
        preview: "注册表列出了当前正在运行的角色实例。DeepSeek 的实例编号可以与 03:17 的记录进行核对。",
        interaction_type: "inspect",
      },
    );
  }
  const visibleHotspots = hasAuthoredHotspots ? state.available_hotspots : fallbackHotspots;
  const availableHotspots = new Map(
    visibleHotspots.map((hotspot) => [hotspot.hotspot_id, hotspot]),
  );
  if (!hasAuthoredHotspots) {
    latestInvestigationState = { ...state, available_hotspots: visibleHotspots };
  }
  for (const button of investigationButtons) {
    const isAvailable = availableHotspots.has(button.dataset.hotspotId);
    const wasHidden = button.hidden;
    button.hidden = !isAvailable;
    if (isAvailable && wasHidden) {
      button.classList.add("is-newly-unlocked");
      button.addEventListener(
        "animationend",
        () => button.classList.remove("is-newly-unlocked"),
        { once: true },
      );
    }
    const hotspotState = state.hotspots?.[button.dataset.hotspotId];
    button.classList.toggle("is-completed", hotspotState === "completed");
  }
  if (claudePrivateInterview) {
    claudePrivateInterview.hidden = !state.private_interview_challenges?.claude;
  }
  if (doubaoPrivateInterview) {
    doubaoPrivateInterview.hidden = !state.private_interview_challenges?.doubao;
  }
  if (gptPrivateInterview) {
    gptPrivateInterview.hidden = !state.private_interview_challenges?.chatgpt;
  }
  // docs/12 §39 Task 1: reconcile the stage against the authoritative state —
  // the Frontend never infers who is on stage from plot conditions.
  stage.applyState(state.presentation_state);
}

function openInvestigationDetail(hotspotId) {
  if (!gameModal || !modalTitle || !investigationPanel) return;
  const hotspot = latestInvestigationState?.available_hotspots?.find(
    (item) => item.hotspot_id === hotspotId,
  );
  if (!hotspot) {
    status.textContent = "这里暂时无法调查。先留意房间里的其他异常。";
    return;
  }
  selectedHotspotId = hotspotId;
  const completed = latestInvestigationState?.hotspots?.[hotspotId] === "completed";
  modalTitle.textContent = hotspot.title;
  investigationPreview.textContent = hotspot.preview;
  investigationProgress.textContent = completed
    ? "这里已经调查完成，可以重新查看已获得的结果。"
    : "这处异常尚未确认。进一步调查后，结果将记录到证据库。";
  investigationConfirm.textContent = completed ? "查看调查结果" : "进一步调查";
  investigationConfirm.disabled = false;
  historyPanel.hidden = true;
  evidencePanel.hidden = true;
  investigationPanel.hidden = false;
  gameModal.hidden = false;
  investigationConfirm.focus?.();
}

investigationConfirm?.addEventListener("click", async () => {
  if (!selectedHotspotId) return;
  const hotspotId = selectedHotspotId;
  investigationConfirm.disabled = true;
  investigationProgress.textContent = "正在核对调查结果……";
  try {
    const data = await sendInvestigationAction("INSPECT_HOTSPOT", hotspotId);
    applyInvestigationState(data.state);
    applyPresentation(data.presentation);
    await openGameModal("evidence", { highlightEvidenceId: data.evidence_id });
    status.textContent = data.outcome === "ALREADY_COMPLETED"
      ? "已重新打开这处调查的结果。"
      : "发现了一条重要线索，已记录到证据库。";
  } catch (error) {
    const message = investigationErrorMessage(error);
    investigationConfirm.disabled = false;
    investigationProgress.textContent = message;
    status.textContent = message;
  }
});

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
    if (!isInteractive()) return;
    const isPaperHotspot = button.dataset.hotspotId === "CH1_NOTE_01";
    if (!isPaperHotspot) {
      openInvestigationDetail(button.dataset.hotspotId);
      return;
    }
    paperPanel.hidden = false;
    try {
      const data = await ensurePaperInvestigation();
      applyInvestigationState(data.state);
      applyPresentation(data.presentation);
      if (data.evidence_id || data.outcome === "ALREADY_COMPLETED") {
        await openGameModal("evidence", { highlightEvidenceId: data.evidence_id });
      } else {
        loadEvidence().catch(() => {});
      }
      status.textContent = data.evidence_id
        ? "发现了一条重要线索。"
        : data.outcome === "ALREADY_COMPLETED"
          ? "这里已经调查完毕，已打开证据库。"
          : "已调查。";
    } catch (error) {
      paperInvestigationPromise = null;
      status.textContent = investigationErrorMessage(error);
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
    const drawWords = (offsetX, offsetY, color) => {
      target.fillStyle = color;
      target.font = "700 28px Georgia, serif";
      target.fillText("03:17", offsetX, offsetY - 47);
      target.font = "600 17px Georgia, serif";
      target.fillText("不要把管理员权限交给", offsetX, offsetY - 10);
      target.fillText("“最会替你解释的人”。", offsetX, offsetY + 18);
      target.font = "600 15px ui-monospace, Consolas, monospace";
      target.fillText("—— V03", offsetX + 96, offsetY + 51);
    };
    target.save();
    target.translate(centerX, centerY);
    target.rotate(-0.045);
    target.textAlign = "center";
    target.textBaseline = "middle";
    drawWords(2, 2, `rgba(67, 49, 36, ${0.23 * alpha})`);
    drawWords(0, 0, `rgba(248, 240, 224, ${0.84 * alpha})`);
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
      // The panel opens immediately for responsiveness, but the backend must
      // first commit INSPECT_HOTSPOT. This also recreates the local guard after
      // a refresh, while preserving the backend's authoritative hotspot state.
      status.textContent = "正在确认纸张状态…";
      await ensurePaperInvestigation();
      const data = await sendInvestigationAction("PAPER_RUBBING_COMPLETE", "CH1_NOTE_01");
      applyInvestigationState(data.state);
      applyPresentation(data.presentation);
      if (data.evidence_id || data.outcome === "ALREADY_COMPLETED") {
        await openGameModal("evidence", { highlightEvidenceId: data.evidence_id });
      }
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

function waitForScriptBeat(duration = 1200) {
  return new Promise((resolve) => {
    const schedule = typeof window !== "undefined" && window.setTimeout
      ? window.setTimeout.bind(window)
      : setTimeout;
    schedule(resolve, duration);
  });
}

async function playScriptSequence(sequence) {
  for (const line of sequence || []) {
    if (line.speaker === "system") {
      // Narration line: no sprite on stage, only the speaker label.
      setSpeaker("system");
      dialogueText.textContent = line.dialogue;
      await waitForScriptBeat();
      continue;
    }
    stage.apply({
      type: "CHARACTER_SHOW",
      character_id: line.speaker,
      emotion: line.emotion || "neutral",
      animation: line.animation === "fade_in" ? "fade_in" : "none",
    });
    setSpeaker(line.speaker);
    if (line.animation && line.animation !== "none" && line.animation !== "fade_in") {
      stage.apply({ type: "CHARACTER_ANIMATION", character_id: line.speaker, animation: line.animation });
    }
    dialogueText.textContent = line.dialogue;
    await waitForScriptBeat();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!isInteractive()) return;
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
      // A committed arrival / final-reveal script plays its presentation
      // actions and authored lines (docs/12 §39 Task 7).
      if (result.presentation_actions?.length) {
        applyPresentationActions(result.presentation_actions);
      }
      if (result.script_sequence?.length) {
        status.textContent = "剧情演出中…";
        await playScriptSequence(result.script_sequence);
      }
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
    // §13.6, §44.1). The structured channel (docs/12 §13) wins over the legacy
    // string directives.
    const presentedCharacter = data.presentation_actions?.length
      ? applyPresentationActions(data.presentation_actions)
      : applyPresentation(data.presentation);
    // The dialogue box always names the actual speaker.
    setSpeaker(data.character_id);
    // If no story directive set the stage, show the speaker (docs/01 §10.1).
    if (!presentedCharacter && stage.focal !== data.character_id) {
      setCharacter(data.character_id);
    }
    // Model-driven emotion + animation (docs/02 §7: 切换表情 / 播放动画).
    const focalCharacter = stage.focal || data.character_id;
    window.galPresentation.apply({
      character: focalCharacter,
      expression: data.emotion,
    });
    window.galPresentation.apply({
      character: focalCharacter,
      animation: data.animation,
    });
    dialogueText.textContent = data.dialogue;
    if (data.script_sequence?.length) {
      status.textContent = "剧情演出中…";
      await playScriptSequence(data.script_sequence);
    }
    status.textContent = data.claim_refs?.length
      ? "已收到角色回应；关键证词已记录。"
      : "已收到角色回应。";
    if (
      data.claim_refs?.length ||
      (data.presentation || []).some((directive) => directive.startsWith("SHOW_CHARACTER")) ||
      data.script_sequence?.length
    ) {
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

// The active DeepSeek line remains backend-authored and idempotent. The
// presentation sequence calls it only at DeepSeek's reveal, never on boot.
async function loadOpeningLine() {
  if (openingLinePromise) return openingLinePromise;
  if (typeof fetch !== "function") {
    return { character_id: "deepseek", dialogue: dialogueText.textContent.trim() };
  }
  openingLinePromise = (async () => {
  try {
    const response = await fetch(`${API_BASE}/api/chat/opening`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!response.ok) return { character_id: "deepseek", dialogue: dialogueText.textContent.trim() };
    const data = await response.json();
    sessionId = data.session_id;
    writeSessionId(sessionId);
    await loadInvestigationState();
    return data;
  } catch (_error) {
    // No backend yet: local presentation still hands off to the static line.
    return { character_id: "deepseek", dialogue: dialogueText.textContent.trim() };
  }
  })();
  return openingLinePromise;
}

async function finishOpening() {
  const opening = await loadOpeningLine();
  const characterId = opening.character_id || "deepseek";
  const line = opening.dialogue || dialogueText.textContent.trim();
  applyPresentation(opening.presentation);
  setSpeaker(characterId);
  setCharacter(characterId);
  characterSprite.classList.remove("is-hidden");
  window.galPresentation.apply({
    character: characterSprite.dataset.character,
    expression: opening.emotion || "normal",
  });
  dialogueText.textContent = line;
  markOpeningCompleted(sessionId);
  if (openingOverlay) openingOverlay.hidden = true;
  setPresentationMode("interactive");
  loadInvestigationState().catch(() => {});
  input.focus();
}

async function startOpening() {
  const runId = ++openingRunId;
  setPresentationMode("opening");
  if (openingOverlay) openingOverlay.hidden = false;
  characterSprite.classList.add("is-hidden");

  // Hand-written DOM stubs used by the existing frontend tests intentionally
  // omit presentation-only nodes; hand off immediately in that environment.
  if (!openingOverlay) {
    characterSprite.classList.remove("is-hidden");
    setPresentationMode("interactive");
    return;
  }

  if (openingWasCompleted(sessionId)) {
    await finishOpening();
    return;
  }

  for (const step of OPENING_SEQUENCE) {
    if (runId !== openingRunId) return;
    renderOpeningStep(step);
    if (step.phase === "deepseek_reveal") {
      const opening = await loadOpeningLine();
      if (runId !== openingRunId) return;
      const characterId = opening.character_id || "deepseek";
      setCharacter(characterId, { fadeIn: true });
      setSpeaker(characterId);
      if (openingSpeaker) openingSpeaker.textContent = CHARACTERS[characterId].name;
      if (openingText) openingText.textContent = opening.dialogue || dialogueText.textContent.trim();
    }
    if (!(await waitForOpening(step.duration, runId))) return;
  }
  if (runId === openingRunId) await finishOpening();
}

async function skipOpening() {
  if (isInteractive()) return;
  openingRunId += 1;
  renderOpeningStep({ phase: "interaction_unlock" });
  await finishOpening();
}

if (skipOpeningButton) skipOpeningButton.addEventListener("click", skipOpening);

if (typeof window !== "undefined") {
  window.galOpening = { skip: skipOpening };
}

startOpening();
