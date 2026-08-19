// docs/13 Task 0 baseline capture: drives headless Chrome via CDP to save
// pre-migration screenshots of the legacy (vanilla-JS) frontend.
//
// Usage: node capture-baseline.mjs
// Requires: Node >= 21 (global fetch + WebSocket), headless Chrome installed.
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME =
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const GAME_URL = "http://127.0.0.1:8000/frontend/index.html";
const WALKTHROUGH_SESSION = "73c4a56df724461797b17e282fbb2d64";
const OUT_DIR = dirname(fileURLToPath(import.meta.url));
const PROFILE_DIR = join(OUT_DIR, ".chrome-profile");
const PORT = 9333;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {
  const chrome = spawn(CHROME, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--hide-scrollbars",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${PROFILE_DIR}`,
    "--window-size=1366,768",
    "about:blank",
  ]);
  // Poll the CDP HTTP endpoint until the browser is ready.
  for (let i = 0; i < 60; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return { chrome, wsUrl: page.webSocketDebuggerUrl };
    } catch {
      /* not up yet */
    }
    await sleep(500);
  }
  throw new Error("Chrome CDP did not become ready");
}

async function cdp(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => {
    ws.onopen = res;
    ws.onerror = () => rej(new Error("ws connect failed"));
  });
  let id = 0;
  const pending = new Map();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    }
  };
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const mid = ++id;
      pending.set(mid, { resolve, reject });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
  return { send, close: () => ws.close() };
}

async function main() {
  rmSync(PROFILE_DIR, { recursive: true, force: true });
  const { chrome, wsUrl } = await launch();
  const client = await cdp(wsUrl);
  await client.send("Page.enable");
  await client.send("Runtime.enable");

  const evaljs = async (expr) => {
    const res = await client.send("Runtime.evaluate", {
      expression: expr,
      returnByValue: true,
      awaitPromise: true,
    });
    if (res.exceptionDetails) throw new Error(res.exceptionDetails.text);
    return res.result.value;
  };
  const shot = async (name) => {
    const res = await client.send("Page.captureScreenshot", { format: "png" });
    const file = join(OUT_DIR, `${name}.png`);
    writeFileSync(file, Buffer.from(res.data, "base64"));
    const jpeg = await client.send("Page.captureScreenshot", {
      format: "jpeg",
      quality: 78,
    });
    const jfile = join(OUT_DIR, `${name}.jpg`);
    writeFileSync(jfile, Buffer.from(jpeg.data, "base64"));
    console.log("saved", file, jfile);
  };
  const waitFor = async (expr, timeoutMs = 90000) => {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      try {
        if (await evaljs(expr)) return true;
      } catch {}
      await sleep(500);
    }
    return false;
  };

  try {
    // --- 1. Fresh game: opening screen ---
    await client.send("Page.navigate", { url: GAME_URL });
    await sleep(4000); // let the opening animation reach room_reveal
    const phase = await evaljs(
      `document.querySelector('.game-shell')?.dataset.openingPhase || 'none'`
    );
    console.log("opening phase:", phase);
    await shot("TASK0_OPENING");

    // --- 2. Opening completes -> DeepSeek single character ---
    const openingDone = await waitFor(
      `!document.querySelector('.game-shell')?.classList.contains('is-opening')`,
      120000
    );
    console.log("opening done:", openingDone);
    const inputEnabled = await evaljs(
      `!document.querySelector('#player-input')?.disabled`
    );
    console.log("player input enabled:", inputEnabled);
    const sessionId = await evaljs(`localStorage.getItem('gal_session_id')`);
    console.log("fresh session id:", sessionId);
    await sleep(800);
    await shot("TASK0_DEEPSEEK_SINGLE");

    // --- 3. Restore walkthrough session -> Claude + DeepSeek double ---
    await evaljs(
      `localStorage.setItem('gal_session_id','${WALKTHROUGH_SESSION}'); location.reload(); true`
    );
    await sleep(4000);
    const claudeShown = await waitFor(
      `!!document.querySelector('#character-stage figure[data-character="claude"]')`,
      60000
    );
    const deepseekShown = await evaljs(
      `(() => { const s = document.querySelector('#character-stage img#character-sprite'); return !!s && getComputedStyle(s).visibility !== 'hidden'; })()`
    );
    console.log("claude sprite:", claudeShown, "deepseek anchor visible:", deepseekShown);
    await sleep(1200);
    await shot("TASK0_CLAUDE_DOUBLE");
  } finally {
    client.close();
    chrome.kill();
    // Chrome may not have released the profile dir yet; retry the cleanup.
    for (let i = 0; i < 5; i++) {
      try {
        rmSync(PROFILE_DIR, { recursive: true, force: true });
        break;
      } catch {
        await sleep(1000);
      }
    }
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
