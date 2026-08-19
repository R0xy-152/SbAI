// Re-capture Task 2 screenshots as PNG (Read tool can display PNG here).
import { spawn } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const VUE_URL = "http://localhost:5174/game";
const OUT_DIR = dirname(fileURLToPath(import.meta.url));
const PROFILE = join(OUT_DIR, ".task2-png-profile");
const PORT = 9342;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch(viewport) {
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
    `--window-size=${viewport.w},${viewport.h}`, "about:blank",
  ]);
  for (let i = 0; i < 60; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return { chrome, wsUrl: page.webSocketDebuggerUrl };
    } catch {}
    await sleep(500);
  }
  throw new Error("Chrome CDP not ready");
}

async function cdp(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = () => j(new Error("ws")); });
  let id = 0; const pending = new Map();
  ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result); } };
  const send = (method, params = {}) => new Promise((resolve, reject) => { const mid = ++id; pending.set(mid, { resolve, reject }); ws.send(JSON.stringify({ id: mid, method, params })); });
  return { send, close: () => ws.close() };
}

async function main() {
  const vp = { name: "1366x768", w: 1366, h: 768 };
  const { chrome, wsUrl } = await launch(vp);
  const client = await cdp(wsUrl);
  await client.send("Page.enable"); await client.send("Runtime.enable");
  try {
    await client.send("Page.navigate", { url: VUE_URL });
    await sleep(6000);
    const r = await client.send("Page.captureScreenshot", { format: "png" });
    const { writeFileSync } = await import("node:fs");
    writeFileSync(join(OUT_DIR, "TASK2_" + vp.name + ".png"), Buffer.from(r.data, "base64"));
    console.log("saved TASK2_" + vp.name + ".png");
  } finally {
    client.close(); chrome.kill();
    const { rmSync } = await import("node:fs");
    for (let i=0;i<5;i++){ try { rmSync(PROFILE,{recursive:true,force:true}); break; } catch { await sleep(800); } }
  }
}
main().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
