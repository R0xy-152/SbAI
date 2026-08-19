// Verify role avatar images actually load (ImageAcrossFade uses backgroundImage
// divs, not <img>), and dialog position vs face zone.
import { spawn } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const VUE_URL = "http://localhost:5174/game";
const OUT_DIR = dirname(fileURLToPath(import.meta.url));
const PROFILE = join(OUT_DIR, ".task2-img-profile");
const PORT = 9346;
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
  const evaljs = async (expr) => { const r = await client.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text); return r.result.value; };
  try {
    await client.send("Page.navigate", { url: VUE_URL });
    await (async () => { const s = Date.now(); while (Date.now() - s < 20000) { try { const n = await evaljs(`document.querySelectorAll('.role-container-transition').length`); if (n >= 2) return; } catch {} await sleep(500); } throw new Error("roles not rendered"); })();
    await sleep(2500);
    const info = await evaljs(`(() => {
      const vw = window.innerWidth, vh = window.innerHeight;
      const roles = Array.from(document.querySelectorAll('.role-container-transition')).map((el, i) => {
        // ImageAcrossFade: two background-image divs (current + fading next)
        const divs = Array.from(el.querySelectorAll('div')).filter(d => getComputedStyle(d).backgroundImage !== 'none');
        const bgImgs = divs.map(d => getComputedStyle(d).backgroundImage.slice(0, 90));
        // natural size of the loaded bitmap via an offscreen probe
        const probe = divs[0] ? new Promise(res => { const im = new Image(); im.onload = () => res({ w: im.naturalWidth, h: im.naturalHeight }); im.onerror = () => res({ w: 0, h: 0 }); im.src = divs[0].style.backgroundImage.replace(/^url\\(["']?/, '').replace(/["']?\\)$/, ''); }) : Promise.resolve({ w: 0, h: 0 });
        return probe.then(({ w, h }) => {
          const rect = el.getBoundingClientRect();
          return { i, rect: { left: Math.round(rect.left), top: Math.round(rect.top), w: Math.round(rect.width), h: Math.round(rect.height) }, natW: w, natH: h, loaded: w > 0, bgImgs };
        });
      });
      return Promise.all(roles);
    })()`);
    console.log(`[${vp.name}] vw=${info.length ? 0 : 0}`); // placeholder
    for (const r of info) console.log(`  role[${r.i}] rect=${JSON.stringify(r.rect)} natural=${r.natW}x${r.natH} loaded=${r.loaded} bg=${JSON.stringify(r.bgImgs)}`);
  } finally {
    client.close(); chrome.kill();
    const { rmSync } = await import("node:fs");
    for (let i=0;i<5;i++){ try { rmSync(PROFILE,{recursive:true,force:true}); break; } catch { await sleep(800); } }
  }
}
main().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
