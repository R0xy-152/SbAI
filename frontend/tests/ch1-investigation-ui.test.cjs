const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const js = fs.readFileSync(path.join(root, "app.js"), "utf8");

assert.match(html, /data-hotspot-id="CH1_NOTE_01"/);
assert.match(html, /data-hotspot-id="CH1_C02_DOOR"/);
assert.match(html, /data-hotspot-id="CH1_CHARACTER_REGISTRY"/);
assert.match(html, /id="switch-chatgpt"/);
assert.match(html, /id="switch-doubao"/);
assert.match(html, /id="rubbing-surface"/);
assert.match(html, /id="rubbing-canvas"/);
assert.match(js, /INSPECT_HOTSPOT/);
assert.match(js, /const isPaperHotspot = button\.dataset\.hotspotId === "CH1_NOTE_01"/);
assert.match(js, /if \(isPaperHotspot\) paperPanel\.hidden = false/);
assert.match(js, /PAPER_RUBBING_COMPLETE/);
assert.match(js, /GRID_COLUMNS = 28/);
assert.match(js, /GRID_ROWS = 15/);
assert.match(js, /COMPLETE_COVERAGE = 0\.38/);
assert.match(js, /destination-out/);
assert.match(js, /api\/game\/action/);
assert.match(js, /api\/game\/state/);
assert.match(html, /id="evidence-panel"/);
assert.match(js, /api\/game\/evidence/);
assert.match(js, /api\/game\/present/);
assert.match(html, /推理请以 \/推理 开头/);
assert.match(js, /api\/game\/deduction/);
assert.match(html, /id="claude-private-interview"/);
assert.match(js, /api\/game\/private-interview\/challenge/);
assert.match(js, /loadInvestigationState\(\)\.catch/);
assert.match(js, /applyPresentation\(data\.presentation\)/);

console.log("CH1 investigation UI wiring: PASS");
