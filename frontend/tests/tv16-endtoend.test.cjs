const assert = require("node:assert/strict");

// TV-16: the complete presentation layer of the vertical slice — character
// switching, event-driven presentation directives, model emotion/animation,
// the speaker label, and the History view (docs/01 §7, §10, §18; docs/03
// §13.6). The backend reply shape is the TV-16 /api/chat contract.

const classes = new Set();
const sprite = {
  dataset: { character: "deepseek", expression: "normal" },
  src: "",
  classList: {
    add: (...names) => names.forEach((name) => classes.add(name)),
    remove: (...names) => names.forEach((name) => classes.delete(name)),
    contains: (name) => classes.has(name),
  },
  addEventListener: () => {},
  offsetWidth: 1,
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

const switchHandlers = {};
const makeSwitch = (id) => ({
  id,
  active: false,
  classList: {
    toggle: (_name, on) => { makeSwitch.toggleState = { id, on }; },
  },
  addEventListener: (_event, handler) => { switchHandlers[id] = handler; },
});
const switchDeepseek = makeSwitch("deepseek");
const switchClaude = makeSwitch("claude");

const historyToggle = { textContent: "查看历史" };
let historyToggleHandler = null;
historyToggle.addEventListener = (_event, handler) => { historyToggleHandler = handler; };
const historyPanel = { hidden: true };
const historyList = {
  children: [],
  replaceChildren: () => { historyList.children = []; },
  appendChild: (item) => historyList.children.push(item),
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
    "#switch-deepseek": switchDeepseek,
    "#switch-claude": switchClaude,
  })[selector],
  createElement: () => ({ textContent: "" }),
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
  // 1. Without a switch the backend decides the speaker (no character_id).
  fetchResult = ok({
    session_id: "sess-1",
    character_id: "deepseek",
    dialogue: "唔……",
    message_count: 1,
    emotion: "neutral",
    animation: "none",
    presentation: [],
  });
  await submit("你好");
  assert.equal(JSON.parse(captured.options.body).character_id, null);
  assert.equal(characterName.textContent, "DeepSeek");

  // 2. The player switches to Claude → the next message carries the pick and
  //    the stage/speaker follow the backend reply.
  switchHandlers.claude();
  fetchResult = ok({
    session_id: "sess-1",
    character_id: "claude",
    dialogue: "……哼，你有什么事？",
    message_count: 2,
    emotion: "neutral",
    animation: "none",
    presentation: [],
  });
  await submit("Claude，你怎么看？");
  assert.equal(JSON.parse(captured.options.body).character_id, "claude");
  assert.equal(characterName.textContent, "Claude");
  assert.equal(sprite.dataset.character, "claude");
  assert.equal(sprite.src, "./public/characters/claude-placeholder.svg");
  assert.equal(dialogue.textContent, "……哼，你有什么事？");

  // 3. A committed event's SHOW_CHARACTER directive overrides the stage even
  //    when someone else speaks (docs/03 §13.6): Claude appears (fade_in),
  //    the dialogue box still names DeepSeek.
  fetchResult = ok({
    session_id: "sess-1",
    character_id: "deepseek",
    dialogue: "唔，我也想知道……",
    message_count: 3,
    emotion: "neutral",
    animation: "none",
    presentation: ["SHOW_CHARACTER claude"],
  });
  await submit("是谁把我们抓来的？");
  assert.equal(sprite.dataset.character, "claude");
  assert.equal(characterName.textContent, "DeepSeek");
  assert.equal(classes.has("is-fading-in"), true);

  // 4. History view fetches the session dialogue and renders it in order.
  fetchResult = ok({
    session_id: "sess-1",
    messages: [
      { role: "player", content: "你好" },
      { role: "character", character_id: "deepseek", content: "唔……" },
      { role: "player", character_id: "claude", content: "Claude，你怎么看？" },
      { role: "character", character_id: "claude", content: "……哼，你有什么事？" },
    ],
  });
  await historyToggleHandler();
  assert.equal(captured.url, "/api/chat/history?session_id=sess-1");
  assert.equal(historyPanel.hidden, false);
  assert.equal(historyToggle.textContent, "收起历史");
  assert.deepEqual(
    historyList.children.map((item) => item.textContent),
    [
      "Player：你好",
      "DeepSeek：唔……",
      "Player：Claude，你怎么看？",
      "Claude：……哼，你有什么事？",
    ],
  );

  console.log("TV-16 end-to-end presentation + history (frontend): PASS");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
