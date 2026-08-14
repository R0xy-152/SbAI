const assert = require("node:assert/strict");

const form = { addEventListener: (_event, handler) => { global.submitHandler = handler; } };
const input = { value: "这里是什么地方？", focus: () => {} };
const dialogue = { textContent: "" };
const status = { textContent: "" };

global.document = {
  querySelector: (selector) => ({
    "#player-form": form,
    "#player-message": input,
    "#dialogue-text": dialogue,
    "#form-status": status,
  })[selector],
};

require("../app.js");
global.submitHandler({ preventDefault: () => {} });

assert.equal(input.value, "");
assert.match(dialogue.textContent, /这里是什么地方？/);
assert.equal(status.textContent, "已发送；已显示本地模拟回复。");

console.log("TV-01 send behavior: PASS");
