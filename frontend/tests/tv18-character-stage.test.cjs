const assert = require("node:assert/strict");

// TV-18: the multi-character CharacterStage (docs/12 §10, §13, §39 Task 2).
// 1-4 sprites share one stage; auto positions follow (i+1)/(n+1) with explicit
// slots winning; emotions/animations are named Presentation Actions; unknown
// actions are rejected and logged; applyState reconciles from the authoritative
// presentation_state; a system script line narrates without a sprite.

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
    appendChild(child) { child.parentNode = this; this.children.push(child); return child; },
    append(...items) { items.forEach((item) => { item.parentNode = this; }); this.children.push(...items); return this; },
    addEventListener(event, handler) {
      if (event === "animationend") this.animationEndHandler = handler;
    },
    offsetWidth: 1,
    remove() {
      if (this.parentNode) {
        const index = this.parentNode.children.indexOf(this);
        if (index !== -1) this.parentNode.children.splice(index, 1);
      }
    },
  };
  node.style.setProperty = (key, value) => { node.style[key] = value; };
  return node;
}

const warnings = [];
global.console = { ...console, warn: (...args) => warnings.push(args.join(" ")) };

const stageNode = makeNode("section");
const sprite = makeNode("img");
sprite.dataset.character = "deepseek";
sprite.dataset.expression = "normal";
// The anchor lives inside #character-stage in the real DOM; mirror that so
// visible() counts it alongside the dynamic sibling figures.
stageNode.appendChild(sprite);

const sendButton = { textContent: "发送", disabled: false };
const form = {
  addEventListener: (_event, handler) => { global.submitHandler = handler; },
  querySelector: () => sendButton,
};
const input = { value: "", disabled: false, focus: () => {} };
const dialogue = { textContent: "" };
const status = { textContent: "" };
const characterName = { textContent: "" };
const gameShell = { dataset: {}, classList: makeNode("main").classList };
const historyToggle = { addEventListener: () => {}, textContent: "查看历史" };
const historyPanel = { hidden: true };
const historyList = { replaceChildren: () => {}, appendChild: () => {} };

global.window = {};
global.document = {
  querySelector: (selector) => ({
    "#player-form": form,
    "#player-message": input,
    "#dialogue-text": dialogue,
    "#form-status": status,
    "#character-sprite": sprite,
    "#character-stage": stageNode,
    "#character-name": characterName,
    ".game-shell": gameShell,
    "#history-toggle": historyToggle,
    "#history-panel": historyPanel,
    "#history-list": historyList,
  })[selector],
  createElement: makeNode,
};

require("../app.js");

const galStage = window.galStage;
assert.ok(galStage, "window.galStage must be exposed");

let captured = null;
let fetchResult;
global.fetch = async (url, options) => {
  captured = { url, options };
  return fetchResult;
};

function ok(body) {
  return { ok: true, status: 200, json: async () => body };
}

function visible() {
  return stageNode.children.filter(
    (child) => child.classList.contains("is-hidden") === false,
  );
}

(async () => {
  // 1. DeepSeek alone is centered on the stage.
  galStage.apply({ type: "CHARACTER_SHOW", character_id: "deepseek" });
  assert.equal(visible().length, 1);
  assert.equal(sprite.style.left, "50%");
  assert.equal(sprite.classList.contains("is-hidden"), false);

  // 2. Claude joins at the explicit RIGHT slot; both share the stage with
  //    distinct positions and the fade_in animation plays.
  galStage.apply({ type: "CHARACTER_SHOW", character_id: "claude", slot: "RIGHT", animation: "fade_in" });
  const claude = stageNode.children.find((child) => child.dataset.character === "claude");
  assert.ok(claude, "a claude sprite is created as a sibling figure");
  assert.equal(claude.classList.contains("is-fading-in"), true);
  assert.equal(claude.style.left, "82%");
  assert.notEqual(sprite.style.left, claude.style.left, "two sprites must not stack");

  // 3. ChatGPT (LEFT) and 豆包 (CENTER) join: every visible sprite gets a
  //    distinct, in-bounds position and the emotion lands on the sprite.
  galStage.apply({ type: "CHARACTER_SHOW", character_id: "chatgpt", slot: "LEFT" });
  galStage.apply({ type: "CHARACTER_SHOW", character_id: "doubao", slot: "CENTER", emotion: "embarrassed" });
  const lefts = visible().map((child) => Number.parseFloat(child.style.left));
  assert.equal(visible().length, 4);
  assert.equal(new Set(lefts).size, 4, "every visible sprite gets a distinct position");
  for (const left of lefts) {
    assert.ok(left >= 6 && left <= 94, `sprite stays inside the stage: ${left}%`);
  }
  const doubao = stageNode.children.find((child) => child.dataset.character === "doubao");
  assert.equal(doubao.dataset.emotion, "embarrassed");

  // 4. CHARACTER_EMOTION switches a sprite's emotion without hiding it.
  galStage.apply({ type: "CHARACTER_EMOTION", character_id: "claude", emotion: "serious" });
  assert.equal(claude.dataset.emotion, "serious");
  assert.equal(claude.classList.contains("is-hidden"), false);

  // 5. CHARACTER_HIDE removes a dynamic sprite entirely (no residual click
  //    area), while the DeepSeek anchor stays in the DOM.
  galStage.apply({ type: "CHARACTER_SHOW", character_id: "chatgpt", slot: "LEFT" });
  galStage.apply({ type: "CHARACTER_HIDE", character_id: "chatgpt" });
  assert.equal(
    stageNode.children.some((child) => child.dataset.character === "chatgpt"),
    false,
    "a hidden dynamic sprite leaves the stage",
  );
  assert.equal(
    stageNode.children.includes(sprite),
    true,
    "hiding someone else never removes the DeepSeek anchor",
  );

  // 6. Unknown actions are rejected and logged; a chat turn survives them.
  const rejected = galStage.apply({ type: "TELEPORT", character_id: "claude" });
  assert.deepEqual(rejected, { applied: false, reason: "unknown_action" });
  const beforeWarnings = warnings.length;
  input.value = "继续";
  fetchResult = ok({
    session_id: "sess-1",
    character_id: "deepseek",
    dialogue: "已知。",
    message_count: 1,
    emotion: "neutral",
    animation: "none",
    presentation: [],
    presentation_actions: [{ type: "TELEPORT", character_id: "deepseek" }],
  });
  await global.submitHandler({ preventDefault: () => {} });
  assert.equal(dialogue.textContent, "已知。");
  assert.ok(warnings.length > beforeWarnings, "an unknown action was logged");

  // 7. Named animations play their classes.
  galStage.apply({ type: "CHARACTER_ANIMATION", character_id: "claude", animation: "slide_in_left" });
  assert.equal(claude.classList.contains("is-sliding-in-left"), true);
  galStage.apply({ type: "CHARACTER_ANIMATION", character_id: "claude", animation: "small_jump" });
  assert.equal(claude.classList.contains("is-small-jumping"), true);

  // 8. Screen effects are bounded named actions on the shell.
  galStage.apply({ type: "SCREEN_GLITCH", intensity: "high" });
  assert.equal(gameShell.classList.contains("is-glitching"), true);
  assert.equal(gameShell.dataset.effectIntensity, "high");
  galStage.apply({ type: "SCREEN_SHAKE", intensity: "high" });
  assert.equal(gameShell.classList.contains("is-screen-shaking"), true);

  // 9. applyState reconciles the stage from the authoritative presentation_state:
  //    visible characters stay, non-visible ones leave, slots are re-applied.
  galStage.apply({ type: "CHARACTER_SHOW", character_id: "chatgpt", slot: "LEFT" });
  galStage.applyState({
    scene: "ROOM_A",
    characters: [
      { character_id: "deepseek", visible: true, emotion: "neutral", slot: null },
      { character_id: "claude", visible: true, emotion: "serious", slot: "RIGHT" },
      { character_id: "chatgpt", visible: false, emotion: "neutral", slot: null },
    ],
    input_mode: "investigation",
  });
  assert.equal(claude.classList.contains("is-hidden"), false);
  assert.equal(claude.style.left, "82%");
  assert.equal(
    stageNode.children.some((child) => child.dataset.character === "chatgpt"),
    false,
    "applyState hides a character the state no longer shows",
  );
  assert.equal(
    stageNode.children.some((child) => child.dataset.character === "doubao"),
    false,
    "applyState hides a character the state no longer lists",
  );

  // 10. A script sequence narrates a system line without a sprite.
  fetchResult = ok({
    session_id: "sess-1",
    character_id: "deepseek",
    dialogue: "有回应",
    message_count: 1,
    emotion: "neutral",
    animation: "none",
    presentation: [],
    presentation_actions: [],
    script_sequence: [
      { speaker: "system", dialogue: "警告：检测到不一致的内存访问痕迹。" },
    ],
  });
  input.value = "03:17 是什么意思？";
  await global.submitHandler({ preventDefault: () => {} });
  assert.equal(characterName.textContent, "系统");
  assert.equal(dialogue.textContent, "警告：检测到不一致的内存访问痕迹。");
  assert.equal(
    stageNode.children.filter((child) => child.classList.contains("is-hidden") === false).length,
    visible().length,
  );

  console.log("TV-18 character stage: PASS");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
