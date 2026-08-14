const assert = require("node:assert/strict");

const classes = new Set();
const listeners = [];
const sprite = {
  dataset: { character: "deepseek", expression: "normal" },
  classList: {
    add: (...names) => names.forEach((name) => classes.add(name)),
    remove: (...names) => names.forEach((name) => classes.delete(name)),
    contains: (name) => classes.has(name),
  },
  addEventListener: (_event, listener) => listeners.push(listener),
  offsetWidth: 1,
};
const form = { addEventListener: () => {}, querySelector: () => ({ textContent: "", disabled: false }) };

global.window = {};
global.document = {
  querySelector: (selector) => ({
    "#player-form": form,
    "#player-message": { value: "", focus: () => {} },
    "#dialogue-text": { textContent: "" },
    "#form-status": { textContent: "" },
    "#character-sprite": sprite,
  })[selector],
};

require("../app.js");

for (const animation of ["fade_in", "fade_out", "shake"]) {
  const result = window.galPresentation.apply({ character: "deepseek", animation });
  assert.equal(result.applied, true);
  listeners.splice(0).forEach((listener) => listener());
}

assert.equal(window.galPresentation.apply({ character: "deepseek", expression: "alert" }).applied, true);
assert.equal(sprite.dataset.expression, "alert");
assert.equal(window.galPresentation.apply({ character: "deepseek", expression: "normal" }).applied, true);
assert.equal(sprite.dataset.expression, "normal");
assert.deepEqual(window.galPresentation.apply({ character: "deepseek", animation: "spin" }), { applied: false, reason: "unknown_animation" });
for (let round = 0; round < 10; round += 1) {
  window.galPresentation.apply({ character: "deepseek", animation: "fade_out" });
  listeners.splice(0).forEach((listener) => listener());
  assert.equal(sprite.classList.contains("is-hidden"), true);

  window.galPresentation.apply({ character: "deepseek", animation: "fade_in" });
  listeners.splice(0).forEach((listener) => listener());
  assert.equal(sprite.classList.contains("is-hidden"), false);

  window.galPresentation.apply({ character: "deepseek", animation: "shake" });
  listeners.splice(0).forEach((listener) => listener());
  assert.equal(sprite.classList.contains("is-shaking"), false);
}

console.log("TV-02 presentation directives: PASS");

