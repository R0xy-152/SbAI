// Verify role avatars via <img> natural sizes + split layout + no overlap.
import { spawn } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const VUE_URL = "http://localhost:5174/game";
const OUT_DIR = dirname(fileURLToPath(import.meta.url));
const PROFILE = join(OUT_DIR, ".task2-img2-profile");
const PORT = 9348;
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
  const viewports = [
    { name: "1366x768", w: 1366, h: 768 },
    { name: "1920x1080", w: 1920, h: 1080 },
  ];
  for (const vp of viewports) {
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
        const roles = Array.from(document.querySelectorAll('.role-container-transition')).map(el => {
          const img = el.querySelector('img');
          const rect = el.getBoundingClientRect();
          return {
            leftPx: Math.round(rect.left), centerPx: Math.round(rect.left + rect.width/2),
            centerPct: +( (rect.left + rect.width/2) / vw * 100 ).toFixed(1),
            w: Math.round(rect.width), h: Math.round(rect.height),
            imgLoaded: img ? img.naturalWidth > 0 : false,
            natW: img ? img.naturalWidth : 0,
          };
        });
        const bgDiv = document.querySelector('.game-background div');
        const bgRect = bgDiv ? bgDiv.getBoundingClientRect() : null;
        const dlgRect = (() => { const d = document.querySelector('#inputMessage'); if (!d) return null; const r = d.getBoundingClientRect(); return { topPct: +(r.top/vh*100).toFixed(1) }; })();
        return { vw, vh, roles, bgFull: bgRect ? (bgRect.width >= vw-1 && bgRect.height >= vh-1) : false, dlgTopPct: dlgRect?.topPct ?? null };
      })()`);
      const c0 = info.roles[0]?.centerPct ?? 0, c1 = info.roles[1]?.centerPct ?? 0;
      const overlap = info.roles.length === 2 && Math.abs(c0 - c1) < 5;
      console.log(`\n[${vp.name}] vw=${info.vw} vh=${info.vh}`);
      info.roles.forEach((r, i) => console.log(`  role[${i}] center=${r.centerPx}px(${r.centerPct}%) w=${r.w} h=${r.h} imgLoaded=${r.imgLoaded} natW=${r.natW}`));
      console.log(`  bgFull (no white borders): ${info.bgFull}`);
      console.log(`  dialog top: ${info.dlgTopPct}% of vh`);
      console.log(`  SPLIT LAYOUT (centers apart): ${overlap ? "FAIL - overlapping" : "PASS"}`);
    } finally {
      client.close(); chrome.kill();
      const { rmSync } = await import("node:fs");
      for (let i=0;i<5;i++){ try { rmSync(PROFILE,{recursive:true,force:true}); break; } catch { await sleep(800); } }
    }
  }
}
main().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
