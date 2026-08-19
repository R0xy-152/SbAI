// docs/13 Task 1 browser verification: load the Vue app in headless Chrome and
// assert (1) it renders, (2) the /api/health probe resolves, (3) no Tauri refs.
import { spawn } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const VUE_URL = "http://localhost:5173/";
const OUT_DIR = dirname(fileURLToPath(import.meta.url));
const PROFILE = join(OUT_DIR, ".vue-profile");
const PORT = 9334;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
    "--window-size=1366,768", "about:blank",
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
  const { chrome, wsUrl } = await launch();
  const client = await cdp(wsUrl);
  await client.send("Page.enable"); await client.send("Runtime.enable");
  const evaljs = async (expr) => { const r = await client.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text); return r.result.value; };
  const shot = async (name) => { const r = await client.send("Page.captureScreenshot", { format: "jpeg", quality: 78 }); const { writeFileSync } = await import("node:fs"); writeFileSync(join(OUT_DIR, name + ".jpg"), Buffer.from(r.data, "base64")); console.log("saved", name + ".jpg"); };

  const logs = [];
  client.send("Runtime.consoleAPICalled", () => {}).catch(()=>{});
  try {
    await client.send("Page.navigate", { url: VUE_URL });
    // wait for title + backend status
    const done = await (async () => { const s = Date.now(); while (Date.now() - s < 20000) { try { const t = await evaljs(`window.__galTitle || ''`); const backend = await evaljs(`(() => { const el = document.body.innerHTML; return el.includes('后端已连接') ? 'connected' : el.includes('后端未连接') ? 'disconnected' : 'pending'; })()`); if (backend !== 'pending') return backend; } catch {} await sleep(500); } return 'timeout'; })();
    const bodyText = await evaljs(`document.body.innerText`);
    const htmlHasTauri = await evaljs(`document.documentElement.outerHTML.includes('tauri') || Array.from(document.querySelectorAll('script')).some(s => (s.src||'').includes('tauri'))`);
    console.log("backend probe:", done);
    console.log("title rendered:", bodyText.includes("完蛋") ? "yes" : "no");
    console.log("menu items:", JSON.stringify(bodyText.split("\n").map(s=>s.trim()).filter(Boolean).slice(0,8)));
    console.log("tauri refs:", htmlHasTauri ? "FOUND (BAD)" : "none (good)");
    await sleep(1000);
    await shot("TASK1_VUE_TITLE");
  } finally {
    client.close(); chrome.kill();
    const { rmSync } = await import("node:fs");
    for (let i=0;i<5;i++){ try { rmSync(PROFILE,{recursive:true,force:true}); break; } catch { await sleep(800); } }
  }
}
main().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
