const assert = require("node:assert/strict");

// TV-17: the active opening line (docs/01 §4). On load the frontend asks the
// backend for the opening once and renders the returned line — no player input
// needed. The backend is idempotent; an empty dialogue means "already opened".

const classes = new Set();
const sprite = {
  dataset: { character: "deepseek", expression: "normal" },
  src: "",
  classList: {
    add: (...names) => names.forEach((name) => classes.add(name)),
    remove: (...names) => names.forEach((name) => classes.delete(name)),
    contains: (name) => classes.has(name),
    toggle: (name, force) => {
      if (force === true) classes.add(name);
      else if (force === false) classes.delete(name);
      else if (classes.has(name)) classes.delete(name);
      else classes.add(name);
    },
  },
  addEventListener: () => {},
  offsetWidth: 1,
  style: { setProperty: () => {} },
};

const sendButton = { textContent: "发送", disabled: false };
const form = {
  addEventListener: (_event, handler) => { global.submitHandler = handler; },
  querySelector: () => sendButton,
};
const input = { value: "", disabled: false, focus: () => {} };
const dialogue = { textContent: "" };
const status = { textContent: "" };
const characterName = { textContent: "" };
const gameShell = { dataset: {}, classList: { toggle: () => {} } };
const openingOverlay = { hidden: false };
const openingSpeaker = { textContent: "" };
const openingText = { textContent: "" };
const skipOpening = { addEventListener: (_event, handler) => { global.skipOpening = handler; } };

const historyToggle = { textContent: "查看历史" };
historyToggle.addEventListener = () => {};
const historyPanel = { hidden: true };
const historyList = {
  children: [],
  replaceChildren: () => { historyList.children = []; },
  appendChild: (item) => historyList.children.push(item),
};

const stored = {};
global.localStorage = {
  getItem: (key) => stored[key] || null,
  setItem: (key, value) => { stored[key] = value; },
};
global.window = {};
global.document = {
  querySelector: (selector) => ({
    "#player-form": form,
    "#player-message": input,
    "#dialogue-text": dialogue,
    "#form-status": status,
    "#character-sprite": sprite,
    "#character-stage": { appendChild: () => {} },
    "#character-name": characterName,
    ".game-shell": gameShell,
    "#opening-overlay": openingOverlay,
    "#opening-speaker": openingSpeaker,
    "#opening-text": openingText,
    "#skip-opening": skipOpening,
    "#history-toggle": historyToggle,
    "#history-panel": historyPanel,
    "#history-list": historyList,
  })[selector],
  createElement: () => ({ textContent: "" }),
};

const captured = [];
global.fetch = async (url, options) => {
  captured.push({ url, options });
  return {
    ok: true,
    status: 200,
    json: async () => ({
      session_id: "sess-1",
      character_id: "deepseek",
      dialogue: "……你醒了。别怕，我们先弄清楚这里发生了什么。",
      message_count: 0,
      emotion: "neutral",
      animation: "none",
      presentation: [],
    }),
  };
};

require("../app.js");

(async () => {
  assert.equal(input.disabled, true, "opening must lock input before the handoff");
  await global.window.galOpening.skip();

  assert.equal(captured[0].url, "/api/chat/opening");
  assert.equal(captured[0].options.method, "POST");
  assert.equal(JSON.parse(captured[0].options.body).session_id, null);
  assert.equal(captured[1].url, "/api/game/state?session_id=sess-1");
  assert.equal(dialogue.textContent, "……你醒了。别怕，我们先弄清楚这里发生了什么。");
  assert.equal(characterName.textContent, "DeepSeek");
  assert.equal(sprite.dataset.character, "deepseek");
  assert.equal(stored["gal_session_id"], "sess-1");
  assert.equal(stored["gal_opening_completed:sess-1"], "true");
  assert.equal(input.disabled, false, "skip must reach the interactive handoff");

  console.log("TV-17 scripted opening (frontend): PASS");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
