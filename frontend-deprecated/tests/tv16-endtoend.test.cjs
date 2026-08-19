const assert = require("node:assert/strict");

// TV-16: the complete presentation layer of the vertical slice — character
// backend-selected speakers, event-driven presentation directives, model emotion/animation,
// the speaker label, and the History view (docs/01 §7, §10, §18; docs/03
// §13.6). The backend reply shape is the TV-16 /api/chat contract. The stage
// holds a multi-character cast (docs/12 §10): a new speaker is ensured as a
// sibling sprite rather than overwriting DeepSeek's anchor.

function makeNode(tag) {
  const node = {
    tagName: tag,
    dataset: {},
    style: {},
    children: [],
    classList: {
      _set: new Set(),
      add(...names) { names.forEach((name) => this._set.add(name)); },
      remove(...names) { names.forEach((name) => this._set.delete(name)); },
      contains(name) { return this._set.has(name); },
      toggle(name, force) {
        if (force === undefined) {
          if (this._set.has(name)) { this._set.delete(name); return false; }
          this._set.add(name); return true;
        }
        if (force) this._set.add(name); else this._set.delete(name);
        return force;
      },
    },
    appendChild(child) { this.children.push(child); return child; },
    append(...items) { this.children.push(...items); },
    addEventListener(event, handler) {
      if (event === "click") this.clickHandler = handler;
    },
    offsetWidth: 1,
    remove() {},
  };
  node.style.setProperty = (key, value) => { node.style[key] = value; };
  return node;
}

const stage = makeNode("section");
const sprite = makeNode("img");
sprite.dataset.character = "deepseek";
sprite.dataset.expression = "normal";
sprite.classList.add("is-hidden");

const sendButton = { textContent: "发送", disabled: false };
const form = {
  addEventListener: (_event, handler) => { global.submitHandler = handler; },
  querySelector: () => sendButton,
};
const input = { value: "", disabled: false, focus: () => {} };
const dialogue = { textContent: "" };
const status = { textContent: "" };
const characterName = { textContent: "" };

const historyToggle = { textContent: "查看历史" };
let historyToggleHandler = null;
historyToggle.addEventListener = (_event, handler) => { historyToggleHandler = handler; };
const evidenceToggle = { textContent: "证据" };
let evidenceToggleHandler = null;
evidenceToggle.addEventListener = (_event, handler) => { evidenceToggleHandler = handler; };
const historyPanel = { hidden: true };
const historyList = {
  children: [],
  replaceChildren: () => { historyList.children = []; },
  appendChild: (item) => historyList.children.push(item),
};
const evidencePanel = { hidden: true };
const evidenceEmpty = { hidden: false };
const evidenceList = {
  children: [],
  replaceChildren: () => { evidenceList.children = []; },
  appendChild: (item) => evidenceList.children.push(item),
};
const gameModal = { hidden: true };
let modalClickHandler = null;
gameModal.addEventListener = (_event, handler) => { modalClickHandler = handler; };
const modalTitle = { textContent: "" };
const modalClose = { focus: () => {} };
let modalCloseHandler = null;
modalClose.addEventListener = (_event, handler) => { modalCloseHandler = handler; };
let keydownHandler = null;

global.window = {};
global.document = {
  querySelector: (selector) => ({
    "#player-form": form,
    "#player-message": input,
    "#dialogue-text": dialogue,
    "#form-status": status,
    "#character-sprite": sprite,
    "#character-stage": stage,
    "#character-name": characterName,
    "#history-toggle": historyToggle,
    "#evidence-toggle": evidenceToggle,
    "#history-panel": historyPanel,
    "#history-list": historyList,
    "#evidence-panel": evidencePanel,
    "#evidence-empty": evidenceEmpty,
    "#evidence-list": evidenceList,
    "#game-modal": gameModal,
    "#modal-title": modalTitle,
    "#modal-close": modalClose,
  })[selector],
  createElement: makeNode,
  addEventListener: (_event, handler) => { keydownHandler = handler; },
};

require("../app.js");

let captured = null;
let fetchResult;
global.fetch = async (url, options) => {
  captured = { url, options };
  if (fetchResult instanceof Error) throw fetchResult;
  if (typeof fetchResult === "function") return fetchResult(url, options);
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
    presentation_actions: [],
  });
  await submit("你好");
  assert.equal("character_id" in JSON.parse(captured.options.body), false);
  assert.equal(characterName.textContent, "DeepSeek");
  assert.equal(sprite.classList.contains("is-hidden"), false);

  // 2. The backend independently selects Claude for the next public turn; the
  //    stage/speaker follow its reply. Claude is a sibling sprite, not a
  //    re-labelled DeepSeek anchor.
  fetchResult = ok({
    session_id: "sess-1",
    character_id: "claude",
    dialogue: "……哼，你有什么事？",
    message_count: 2,
    emotion: "neutral",
    animation: "none",
    presentation: [],
    presentation_actions: [],
  });
  await submit("Claude，你怎么看？");
  assert.equal("character_id" in JSON.parse(captured.options.body), false);
  assert.equal(characterName.textContent, "Claude");
  const claude = stage.children.find((child) => child.dataset.character === "claude");
  assert.ok(claude, "a claude sprite is ensured on the stage");
  assert.equal(claude.children[0].src, "./public/characters/claude-main.png");
  assert.equal(claude.classList.contains("is-hidden"), false);
  assert.equal(sprite.dataset.character, "deepseek", "DeepSeek's anchor is untouched");
  assert.equal(dialogue.textContent, "……哼，你有什么事？");

  // 3. A committed event's SHOW_CHARACTER directive overrides the stage even
  //    when someone else speaks (docs/03 §13.6): Claude fades in again, the
  //    dialogue box still names DeepSeek.
  fetchResult = ok({
    session_id: "sess-1",
    character_id: "deepseek",
    dialogue: "唔，我也想知道……",
    message_count: 3,
    emotion: "neutral",
    animation: "none",
    presentation: ["SHOW_CHARACTER claude"],
    presentation_actions: [
      { type: "CHARACTER_SHOW", character_id: "claude", animation: "fade_in", emotion: "serious" },
    ],
  });
  await submit("是谁把我们抓来的？");
  assert.equal(characterName.textContent, "DeepSeek");
  assert.equal(claude.classList.contains("is-fading-in"), true);

  // 4. History opens in the shared modal and renders in order.
  fetchResult = ok({
    session_id: "sess-1",
    messages: [
      { role: "player", content: "你好" },
      { role: "character", character_id: "deepseek", content: "唔……" },
      { role: "player", content: "Claude，你怎么看？" },
      { role: "character", character_id: "claude", content: "……哼，你有什么事？" },
    ],
  });
  await historyToggleHandler();
  assert.equal(captured.url, "/api/chat/history?session_id=sess-1");
  assert.equal(gameModal.hidden, false);
  assert.equal(modalTitle.textContent, "对话历史");
  assert.equal(historyPanel.hidden, false);
  assert.equal(evidencePanel.hidden, true);
  assert.deepEqual(
    historyList.children.map((item) => item.textContent),
    [
      "Player：你好",
      "DeepSeek：唔……",
      "Player：Claude，你怎么看？",
      "Claude：……哼，你有什么事？",
    ],
  );

  // 5. Close controls restore the unchanged game view; Escape works too.
  modalCloseHandler();
  assert.equal(gameModal.hidden, true);
  assert.equal(historyPanel.hidden, true);
  await historyToggleHandler();
  keydownHandler({ key: "Escape" });
  assert.equal(gameModal.hidden, true);

  // 6. Evidence uses the same modal, rather than expanding below the toolbar.
  let evidenceLoadCount = 0;
  fetchResult = (url) => {
    if (url === "/api/game/evidence?session_id=sess-1") {
      evidenceLoadCount += 1;
      return ok([{
        evidence_id: "EV01",
        title: "纸张",
        summary: "03:17",
        presented_to: evidenceLoadCount > 1 ? ["deepseek"] : [],
      }]);
    }
    throw new Error(`Unexpected request: ${url}`);
  };
  await evidenceToggleHandler();
  assert.equal(captured.url, "/api/game/evidence?session_id=sess-1");
  assert.equal(gameModal.hidden, false);
  assert.equal(modalTitle.textContent, "证据");
  assert.equal(historyPanel.hidden, true);
  assert.equal(evidencePanel.hidden, false);
  assert.equal(evidenceList.children[0].children.length, 2);
  assert.equal(evidenceLoadCount, 1);
  modalClickHandler({ target: gameModal });
  assert.equal(gameModal.hidden, true);

  console.log("TV-16 presentation + modal history/evidence (frontend): PASS");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
