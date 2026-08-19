// docs/13 Task 5 acceptance: Title Screen
//   - 首次进入不是直接落入对话场景（落 Title）
//   - 无存档时 Continue 正确禁用/提示
//   - New Game 创建新 Session（→ GameView Opening）
//   - Back to Title 可正常工作
//   - resize 时主菜单不溢出
//   - 视觉风格与游戏内 UI 一致（背景图加载）
// Runs against the live backend (8000) + vite (5175) via headless Chrome CDP.
import { spawn } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const VUE_URL = process.env.VUE_URL || "http://localhost:5175/";
const OUT_DIR = dirname(fileURLToPath(import.meta.url));
const PROFILE = join(OUT_DIR, ".task5-profile");
const PORT = 9358;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launchChrome() {
  const chrome = spawn(CHROME, ["--headless=new","--disable-gpu","--no-sandbox","--hide-scrollbars",`--remote-debugging-port=${PORT}`,`--user-data-dir=${PROFILE}`,`--window-size=1366,768`,`about:blank`]);
  let wsUrl; for (let i=0;i<60;i++){ try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); const p = l.find(t=>t.type==="page"); if (p){ wsUrl=p.webSocketDebuggerUrl; break; } } catch {} await sleep(500); }
  if (!wsUrl) throw new Error("chrome CDP not reachable");
  const ws = new WebSocket(wsUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
  let id=0; const pend=new Map(); const consoleMsgs=[];
  ws.onmessage=(ev)=>{const m=JSON.parse(ev.data);
    if(m.method==="Runtime.consoleAPICalled"){consoleMsgs.push(m.params.type+": "+m.params.args.map(a=>a.value||a.description||"").join(" "));}
    if(m.id&&pend.has(m.id)){const p=pend.get(m.id);pend.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result);}};
  const send=(method,params={})=>new Promise((res,rej)=>{const mid=++id;pend.set(mid,{resolve:res,reject:rej});ws.send(JSON.stringify({id:mid,method,params}));});
  await send("Page.enable"); await send("Runtime.enable");
  const evaljs=async(expr)=>{const r=await send("Runtime.evaluate",{expression:expr,returnByValue:true,awaitPromise:true}); if(r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result.value;};
  return { ws, chrome, evaljs, consoleMsgs, send };
}

async function waitFor(evaljs, expr, timeout = 20000, label = "condition") {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try { if (await evaljs(expr)) return true; } catch {}
    await sleep(400);
  }
  throw new Error(`timeout waiting for ${label}: ${expr}`);
}

async function main() {
  const results = [];
  const check = (name, ok, detail) => { results.push({ name, ok: !!ok, detail: detail ?? "" }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`); };

  const c = await launchChrome();
  await c.send("Page.navigate", { url: VUE_URL });
  // 首次进入：清空 localStorage 后 reload，应落 Title 而非直接落入对话场景
  await waitFor(c.evaljs, `document.querySelector('nav button') !== null`, 30000, "title nav mount");
  await c.evaljs(`localStorage.clear()`);
  await c.send("Page.reload", { ignoreCache: true });
  await waitFor(c.evaljs, `document.querySelectorAll('nav button').length === 4 && document.querySelector('h1')?.textContent?.trim() !== ''`, 30000, "title menu after clear");

  // ── 1. 首次进入落 Title（不是对话场景）──
  const title = await c.evaljs(`(() => {
    const h1 = document.querySelector('h1')?.textContent?.trim() || '';
    const buttons = Array.from(document.querySelectorAll('nav button')).map(b => b.textContent.trim());
    const hasGameInput = !!document.querySelector('#inputMessage');
    return { h1, buttons, hasGameInput };
  })()`);
  check("首次进入落 Title（非对话场景）", title.hasGameInput === false && title.buttons.length === 4, `h1="${title.h1.slice(0,12)}" buttons=${JSON.stringify(title.buttons)}`);
  check("菜单含 开始/继续/读取/设置", ["开始游戏","继续游戏","读取存档","设置"].every(b => title.buttons.includes(b)), JSON.stringify(title.buttons));

  // ── 2. 无存档时 Continue 禁用 ──
  await sleep(400);
  const contState = await c.evaljs(`(() => {
    const btn = Array.from(document.querySelectorAll('nav button')).find(b => b.textContent.trim() === '继续游戏');
    return btn ? { disabled: btn.disabled, title: btn.getAttribute('title') || '' } : null;
  })()`);
  check("无存档时 Continue 禁用", !!contState && contState.disabled === true, JSON.stringify(contState));

  // ── 3. 背景图加载（视觉与游戏内一致）──
  const bg = await c.evaljs(`(() => {
    const img = Array.from(document.querySelectorAll('img')).find(i => (i.currentSrc || i.src || '').includes('background1'));
    return img ? img.naturalWidth : 0;
  })()`);
  check("背景图加载（与游戏内一致）", bg > 0, `naturalWidth=${bg}`);

  // ── 4. New Game → GameView Opening ──
  await c.evaljs(`Array.from(document.querySelectorAll('nav button')).find(b => b.textContent.trim() === '开始游戏').click()`);
  await waitFor(c.evaljs, `document.querySelector('#inputMessage') !== null`, 30000, "gameview mount");
  await waitFor(c.evaljs, `(document.querySelector('#character')?.textContent?.trim() || '') !== '' && (document.querySelector('#inputMessage')?.value || '') !== ''`, 30000, "opening line typed");
  const newGame = await c.evaljs(`(() => ({
    speaker: document.querySelector('#character')?.textContent?.trim() || '',
    line: document.querySelector('#inputMessage')?.value || '',
    sid: localStorage.getItem('gal_session_id') || '',
  }))()`);
  check("New Game 创建新 Session + Opening", !!newGame.sid && !!newGame.line, `sid=${newGame.sid.slice(0,8)} speaker=${newGame.speaker}`);
  check("Opening 说话者 = DeepSeek", newGame.speaker.toLowerCase().includes('deepseek'), newGame.speaker);

  // ── 5. Back to Title ──
  const backBtn = await c.evaljs(`(() => {
    const btn = Array.from(document.querySelectorAll('header button')).find(b => b.textContent.includes('返回标题'));
    if (!btn) return false; btn.click(); return true;
  })()`);
  check("Back to Title 按钮存在", !!backBtn, "");
  await waitFor(c.evaljs, `document.querySelector('h1') !== null && !!document.querySelector('#inputMessage') === false`, 10000, "back at title");
  check("Back to Title 回到标题", true, "");

  // ── 6. resize 不溢出 ──
  await c.send("Emulation.setDeviceMetricsOverride", { width: 360, height: 640, deviceScaleFactor: 1, mobile: false });
  await sleep(500);
  const overflow = await c.evaljs(`(() => {
    const nav = document.querySelector('nav');
    if (!nav) return { nav: false };
    const r = nav.getBoundingClientRect();
    const scrolled = document.documentElement.scrollWidth > document.documentElement.clientWidth
      || document.documentElement.scrollHeight > document.documentElement.clientHeight;
    return { nav: true, left: Math.round(r.left), right: Math.round(r.right), vw: window.innerWidth, scrolled };
  })()`);
  const noOverflow = overflow.nav === true && overflow.left >= 0 && overflow.right <= overflow.vw && overflow.scrolled === false;
  check("resize 时主菜单不溢出", noOverflow, JSON.stringify(overflow));
  await c.send("Emulation.clearDeviceMetricsOverride");

  c.ws.close(); c.chrome.kill();
  for (let i=0;i<5;i++){ try { const { rmSync } = await import("node:fs"); rmSync(PROFILE,{recursive:true,force:true}); break; } catch { await sleep(800); } }

  const failed = results.filter(r => !r.ok);
  console.log(`\n=== Task 5 summary: ${results.length - failed.length}/${results.length} PASS ===`);
  if (failed.length) { console.log("FAILED:"); failed.forEach(f => console.log(" - " + f.name)); process.exit(1); }
}

main().catch(e => { console.error("FATAL:", e.message); process.exit(1); });
