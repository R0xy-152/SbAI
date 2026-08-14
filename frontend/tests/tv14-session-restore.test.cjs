const assert = require("node:assert/strict");

// TV-14: session id survives a refresh via localStorage.
const store = { gal_session_id: "sess-restored" };
global.localStorage = {
  getItem: (key) => (key in store ? store[key] : null),
  setItem: (key, value) => {
    store[key] = String(value);
  },
};

const sendButton = { textContent: "发送", disabled: false };
const form = {
  addEventListener: (_event, handler) => {
    global.submitHandler = handler;
  },
  querySelector: () => sendButton,
};
const input = { value: "", disabled: false, focus: () => {} };
const dialogue = { textContent: "" };
const status = { textContent: "" };
const characterName = { textContent: "" };
const historyPanel = { hidden: true };
const historyList = { replaceChildren: () => {}, appendChild: () => {} };
const historyToggle = { addEventListener: () => {}, textContent: "查看历史" };
const switchButton = () => ({
  addEventListener: () => {},
  classList: { toggle: () => {} },
});
const sprite = {
  dataset: {},
  classList: { add: () => {}, remove: () => {}, contains: () => false },
  addEventListener: () => {},
  offsetWidth: 1,
};

global.window = {};
global.document = {
  querySelector: (selector) => ({
    "#player-form": form,
    "#player-message": input,
    "#dialogue-text": dialogue,
    "#form-status": status,
    "#character-sprite": sprite,
    "#character-name": characterName,
    "#history-toggle": historyToggle,
    "#history-panel": historyPanel,
    "#history-list": historyList,
    "#switch-deepseek": switchButton(),
    "#switch-claude": switchButton(),
  })[selector],
};

require("../app.js");

let captured = null;
let fetchResult;
global.fetch = async (url, options) => {
  captured = { url, options };
  if (fetchResult instanceof Error) throw fetchResult;
  return fetchResult;
};

function ok(body) {
  return { ok: true, status: 200, json: async () => body };
}

function submit(text) {
  input.value = text;
  return global.submitHandler({ preventDefault: () => {} });
}

(async () => {
  // 1. After a refresh the stored session id is sent instead of null.
  fetchResult = ok({
    session_id: "sess-restored",
    character_id: "deepseek",
    dialogue: "欢迎回来",
    message_count: 7,
  });
  await submit("我回来了");
  assert.equal(JSON.parse(captured.options.body).session_id, "sess-restored");

  // 2. A new session id from the backend is written back to storage.
  fetchResult = ok({
    session_id: "sess-new",
    character_id: "deepseek",
    dialogue: "新会话",
    message_count: 1,
  });
  await submit("重开一局");
  assert.equal(store.gal_session_id, "sess-new");

  // 3. The stored id is reused on the following request.
  await submit("再来一句");
  assert.equal(JSON.parse(captured.options.body).session_id, "sess-new");

  console.log("TV-14 session restore (frontend): PASS");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
