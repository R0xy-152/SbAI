import { spawn } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const VUE_URL = "http://localhost:5174/game";
const OUT_DIR = dirname(fileURLToPath(import.meta.url));
const PROFILE = join(OUT_DIR, ".task2-profile");
const PORT = 9340;
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
  const results = {};
  for (const vp of viewports) {
    const { chrome, wsUrl } = await launch(vp);
    const client = await cdp(wsUrl);
    await client.send("Page.enable"); await client.send("Runtime.enable");
    const evaljs = async (expr) => { const r = await client.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text); return r.result.value; };
    const shot = async (name) => { const r = await client.send("Page.captureScreenshot", { format: "jpeg", quality: 80 }); const { writeFileSync } = await import("node:fs"); writeFileSync(join(OUT_DIR, name + ".jpg"), Buffer.from(r.data, "base64")); console.log("saved", name + ".jpg"); };

    try {
      await client.send("Page.navigate", { url: VUE_URL });
      await (async () => { const s = Date.now(); while (Date.now() - s < 20000) { try { const n = await evaljs(`document.querySelectorAll('.role-container-transition').length`); if (n >= 2) return; } catch {} await sleep(500); } throw new Error("roles not rendered in 20s"); })();
      await sleep(1500);

      // sample the presentation store directly + the emotion label over 2 cycles
      const emoSamples = [];
      const animSamples = [];
      for (let i = 0; i < 3; i++) {
        const s = await evaljs(`(() => {
          const emo = document.querySelector('#character-emotion')?.textContent?.trim() || '';
          const anim = document.querySelector('.role-container-transition')?.className || '';
          const imgAnim = document.querySelector('.role-container-transition img, .role-container-transition div[class*="normal"], .role-container-transition div[class*="angry"], .role-container-transition div[class*="happy"], .role-container-transition div[class*="serious"], .role-container-transition div[class*="embarrassed"], .role-container-transition div[class*="suprised"]')?.className || '';
          return { emo, imgAnim };
        })()`);
        emoSamples.push(s.emo);
        animSamples.push(s.imgAnim);
        await sleep(3200);
      }

      const info = await evaljs(`(() => {
        const roles = Array.from(document.querySelectorAll('.role-container-transition')).map(el => {
          const st = getComputedStyle(el);
          return { left: st.left, top: st.top, opacity: st.opacity, img: el.querySelector('img, [class*="background-image"], div')?.className || '' };
        });
        const bgDiv = document.querySelector('.game-background div');
        return {
          roleCount: roles.length,
          roles,
          bgImg: bgDiv ? getComputedStyle(bgDiv).backgroundImage.slice(0, 80) : 'none',
          speaker: document.querySelector('#character')?.textContent?.trim() || '',
          dialogVisible: !!document.querySelector('#inputMessage'),
          bodyText: document.body.innerText,
          noBrand: !/Ling\s?Chat|Ling Ling|Lovely You|Bilibili|诺一钦灵|诺一/.test(document.body.innerText),
        };
      })()`);
      results[vp.name] = { ...info, emoSamples, animSamples, emotionChanged: new Set(emoSamples).size > 1 };

      // layout jump: sprite left stable across emotion change
      const leftBefore = await evaljs(`getComputedStyle(document.querySelectorAll('.role-container-transition')[0]).left`);
      await sleep(3200);
      const leftAfter = await evaljs(`getComputedStyle(document.querySelectorAll('.role-container-transition')[0]).left`);
      results[vp.name].leftStable = leftBefore === leftAfter;

      await shot("TASK2_" + vp.name);
    } finally {
      client.close(); chrome.kill();
      const { rmSync } = await import("node:fs");
      for (let i=0;i<5;i++){ try { rmSync(PROFILE,{recursive:true,force:true}); break; } catch { await sleep(800); } }
    }
  }

  console.log("\n=== RESULTS ===");
  for (const [name, info] of Object.entries(results)) {
    console.log(`\n[${name}]`);
    console.log("  roleCount:", info.roleCount);
    console.log("  roles lefts:", JSON.stringify(info.roles));
    console.log("  bg image:", info.bgImg);
    console.log("  speaker:", info.speaker);
    console.log("  dialogVisible:", info.dialogVisible);
    console.log("  emotionChanged:", info.emotionChanged, "samples:", JSON.stringify(info.emoSamples));
    console.log("  animSamples:", JSON.stringify(info.animSamples));
    console.log("  leftStable (no layout jump):", info.leftStable);
    console.log("  no LingChat brand text:", info.noBrand);
  }
}
main().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
