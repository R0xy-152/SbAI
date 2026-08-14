const assert = require("node:assert/strict");

const form = {
  addEventListener: (_event, handler) => { global.submitHandler = handler; },
  querySelector: () => sendButton,
};
const input = { value: "这里是什么地方？", disabled: false, focus: () => {} };
const sendButton = { textContent: "发送", disabled: false };
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

global.fetch = async () => ({
  ok: true,
  status: 200,
  json: async () => ({
    session_id: "sess-1",
    character_id: "deepseek",
    dialogue: "后端回复：这里是什么地方？",
    message_count: 1,
  }),
});

(async () => {
  await global.submitHandler({ preventDefault: () => {} });

  assert.equal(input.value, "");
  assert.match(dialogue.textContent, /这里是什么地方？/);
  assert.equal(status.textContent, "已收到角色回应。");
  assert.equal(sendButton.disabled, false);

  console.log("TV-01 send behavior: PASS");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
