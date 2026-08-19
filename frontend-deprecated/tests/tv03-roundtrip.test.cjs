const assert = require("node:assert/strict");

const sendButton = { textContent: "发送", disabled: false };
const form = {
  addEventListener: (_event, handler) => { global.submitHandler = handler; },
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
  classList: { add: () => {}, remove: () => {}, contains: () => false, toggle: () => {} },
  addEventListener: () => {},
  offsetWidth: 1,
  style: { setProperty: () => {} },
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
  // 1. First request creates a session and displays the backend reply.
  fetchResult = ok({
    session_id: "sess-abc",
    character_id: "deepseek",
    dialogue: "后端回复：你好",
    message_count: 1,
  });
  await submit("你好");
  assert.equal(input.value, "");
  assert.equal(dialogue.textContent, "后端回复：你好");
  assert.equal(status.textContent, "已收到角色回应。");
  assert.equal(captured.url, "/api/chat");
  assert.deepEqual(JSON.parse(captured.options.body), {
    message: "你好",
    session_id: null,
  });

  // 2. The second request sends the stored session id.
  fetchResult = ok({
    session_id: "sess-abc",
    character_id: "deepseek",
    dialogue: "后端回复：第二句",
    message_count: 2,
  });
  await submit("第二句");
  assert.equal(JSON.parse(captured.options.body).session_id, "sess-abc");
  assert.equal(dialogue.textContent, "后端回复：第二句");

  // 3. Waiting state is visible while a request is in flight.
  let resolveFetch;
  fetchResult = new Promise((resolve) => { resolveFetch = resolve; });
  const pending = submit("阻塞中");
  assert.equal(input.disabled, true);
  assert.equal(sendButton.disabled, true);
  assert.equal(sendButton.textContent, "思考中…");
  resolveFetch(ok({
    session_id: "sess-abc",
    character_id: "deepseek",
    dialogue: "好了",
    message_count: 3,
  }));
  await pending;
  assert.equal(input.disabled, false);
  assert.equal(sendButton.disabled, false);
  assert.equal(sendButton.textContent, "发送");

  // 4. A failure restores the message for retry; the retry then succeeds.
  fetchResult = new Error("network down");
  await submit("会失败吗");
  assert.equal(input.value, "会失败吗");
  assert.equal(status.textContent, "发送失败，请重试。");

  fetchResult = ok({
    session_id: "sess-abc",
    character_id: "deepseek",
    dialogue: "重试成功",
    message_count: 4,
  });
  await submit("会失败吗");
  assert.equal(dialogue.textContent, "重试成功");
  assert.equal(input.value, "");

  // 5. Ten consecutive requests all succeed without UI getting stuck.
  for (let turn = 1; turn <= 10; turn += 1) {
    fetchResult = ok({
      session_id: "sess-abc",
      character_id: "deepseek",
      dialogue: `第 ${turn} 条`,
      message_count: turn,
    });
    await submit(`第 ${turn} 条`);
    assert.equal(dialogue.textContent, `第 ${turn} 条`);
  }

  // 6. A blank message is rejected locally without touching the backend.
  await submit("   ");
  assert.equal(status.textContent, "请先输入一句话。");
  assert.equal(input.value, "   ");

  console.log("TV-03 backend round trip: PASS");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
