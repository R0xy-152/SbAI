// docs/13 Task 4 acceptance: New Session / Player Input / Response /
// Presentation Directive / Character Presence / Emotion / Narrative Event,
// plus 03:17 → Claude appears → Claude interactable, and Vue refresh restore.
// Runs against the live backend (8000) + vite (proxy /api), via headless Chrome CDP.
import { spawn } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const VUE_URL = process.env.VUE_URL || "http://localhost:5175/game";
const API = "http://127.0.0.1:8000";
const OUT_DIR = dirname(fileURLToPath(import.meta.url));
const PROFILE = join(OUT_DIR, ".task4-profile");
const PORT = 9353;
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

// CDP click helper: click by CSS selector and wait
async function cdpClick(evaljs, selector) {
  return evaljs(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (!el) return false; el.click(); return true; })()`);
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

  // ── 1. New Session + Opening ──
  const c1 = await launchChrome();
  await c1.send("Page.navigate", { url: VUE_URL });
  await waitFor(c1.evaljs, `location.host !== '' && document.querySelector('#inputMessage') !== null`, 20000, "page load");
  await c1.evaljs(`localStorage.clear()`);
  await c1.send("Page.reload", { ignoreCache: true });
  await waitFor(c1.evaljs, `document.querySelector('#inputMessage') !== null`, 20000, "dialog mount after clear");
  await waitFor(c1.evaljs, `(document.querySelector('#character')?.textContent?.trim() || '') !== ''`, 20000, "opening speaker");
  await sleep(1200);
  const opening = await c1.evaljs(`(() => {
    const char = document.querySelector('#character')?.textContent?.trim() || '';
    const line = document.querySelector('#inputMessage')?.value || '';
    const session = localStorage.getItem('gal_session_id') || '';
    // Vue 版角色容器是 .role-container-transition；立绘 img 在 RoleSprite 内
    const sprites = Array.from(document.querySelectorAll('.role-container-transition img'))
      .map(i => ({ src: (i.currentSrc || i.src || ''), nw: i.naturalWidth }));
    const bg = Array.from(document.querySelectorAll('img')).some(i => (i.currentSrc || i.src || '').includes('background1'))
      || Array.from(document.querySelectorAll('[style*="background"]')).some(el => (el.style?.backgroundImage || '').includes('background1'));
    return { char, line, session, sprites, bg };
  })()`);
  check("New Session mints session_id", !!opening.session, `id=${opening.session?.slice(0,8)}`);
  check("Opening line displayed", !!opening.line, `line="${opening.line.slice(0,30)}"`);
  check("Opening speaker = DeepSeek", opening.char.toLowerCase().includes("deepseek"), `char=${opening.char}`);
  check("DeepSeek sprite loaded", (opening.sprites?.length ?? 0) > 0 && opening.sprites.every(s => s.nw > 0), `sprites=${JSON.stringify(opening.sprites?.map(s=>s.nw))}`);
  check("Background loaded", !!opening.bg, "");

  // ── 2. Player Input → Response ──
  const sessionId = opening.session;
  // 先推进 opening（点击发送继续，解锁输入）
  await cdpClick(c1.evaljs, "#sendButton");
  await waitFor(c1.evaljs, `!document.querySelector('#inputMessage')?.readOnly`, 10000, "input unlocked");
  // 输入并发送
  const msg1 = "你是谁？这里是什么地方？";
  await c1.evaljs(`(() => { const t = document.querySelector('#inputMessage'); t.value = ${JSON.stringify(msg1)}; t.dispatchEvent(new Event('input')); return true; })()`);
  await cdpClick(c1.evaljs, "#sendButton");
  // 等待回复开始打字（此时说话者仍是 DeepSeek，value 为回复内容）
  await waitFor(c1.evaljs, `(document.querySelector('#inputMessage')?.value || '') !== '' && (document.querySelector('#inputMessage')?.value || '') !== ${JSON.stringify(msg1)}`, 30000, "character response typing");
  const resp1 = await c1.evaljs(`(() => {
    const char = document.querySelector('#character')?.textContent?.trim() || '';
    const line = document.querySelector('#inputMessage')?.value || '';
    return { char, line };
  })()`);
  check("Player message sent → response received", resp1.line.length > 0, `speaker=${resp1.char} line="${resp1.line.slice(0,30)}"`);
  // 回复打字机完成：手动点击推进（LingChat 交互 = 玩家点击继续），解锁输入
  await cdpClick(c1.evaljs, "#sendButton");
  await waitFor(c1.evaljs, `!document.querySelector('#inputMessage')?.readOnly`, 10000, "input unlocked after response");

  // ── 3. 调查纸 → EV01 → 03:17 → Claude 出现 ──
  // 调查入口按钮（底部左侧）
  const clicked = await c1.evaljs(`(() => { const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('调查桌上的纸')); if (!btn) return false; btn.click(); return true; })()`);
  check("investigation entry present", !!clicked, "");
  await waitFor(c1.evaljs, `Array.from(document.querySelectorAll('button')).some(b => b.textContent.includes('调查中')) || Array.from(document.querySelectorAll('div,span')).some(el => el.textContent.includes('03:17 的笔记') || el.textContent.includes('拓印完成'))`, 20000, "paper inspected");
  await waitFor(c1.evaljs, `!document.querySelector('#inputMessage')?.readOnly`, 20000, "input ready after investigation");
  const msg2 = "桌上的笔记提到了 03:17，那是什么？";
  await c1.evaljs(`(() => { const t = document.querySelector('#inputMessage'); t.value = ${JSON.stringify(msg2)}; t.dispatchEvent(new Event('input')); return true; })()`);
  await cdpClick(c1.evaljs, "#sendButton");
  // 03:17 脚本序列（主台词 → system 警告 → claude「比上一次慢。」→ deepseek 反应）：
  // 逐行点击推进，直到说话者变为 Claude。
  await waitFor(c1.evaljs, `(document.querySelector('#character')?.textContent?.trim() || '').toLowerCase().includes('claude')`, 60000, "claude appears (speaker)")
    .catch(async () => {
      // 主台词可能较长，先等主台词出现再持续点击推进
      await waitFor(c1.evaljs, `(document.querySelector('#inputMessage')?.value || '') !== ''`, 20000, "main line");
      for (let i = 0; i < 8; i++) {
        await cdpClick(c1.evaljs, "#sendButton");
        await sleep(600);
        const who = await c1.evaljs(`document.querySelector('#character')?.textContent?.trim() || ''`);
        if (who.toLowerCase().includes('claude')) return;
      }
      throw new Error("claude never appeared");
    });
  await sleep(2000);
  const claudeStage = await c1.evaljs(`(() => {
    const char = document.querySelector('#character')?.textContent?.trim() || '';
    const line = document.querySelector('#inputMessage')?.value || '';
    const spriteCount = document.querySelectorAll('.role-container-transition').length;
    return { char, line, spriteCount };
  })()`);
  check("03:17 → Claude appears (speaker)", claudeStage.char.toLowerCase().includes('claude'), `char=${claudeStage.char}`);
  check("Claude speaks (scripted line)", claudeStage.line.length > 0, `line="${claudeStage.line.slice(0,30)}"`);

  // ── 4. Claude 可对话 ──
  // 03:17 序列播完后 player_input 解锁输入：持续点击推进直到可输入。
  for (let i = 0; i < 6 && !(await c1.evaljs(`!document.querySelector('#inputMessage')?.readOnly`)); i++) {
    await cdpClick(c1.evaljs, "#sendButton");
    await sleep(600);
  }
  await waitFor(c1.evaljs, `!document.querySelector('#inputMessage')?.readOnly`, 10000, "input after incident");
  await c1.evaljs(`(() => { const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Claude'); if (btn) btn.click(); return true; })()`);
  await sleep(500);
  const msg3 = "你知道 03:17 发生了什么吗？";
  await c1.evaljs(`(() => { const t = document.querySelector('#inputMessage'); t.value = ${JSON.stringify(msg3)}; t.dispatchEvent(new Event('input')); return true; })()`);
  await cdpClick(c1.evaljs, "#sendButton");
  await waitFor(c1.evaljs, `(document.querySelector('#character')?.textContent || '').toLowerCase().includes('claude') && (document.querySelector('#inputMessage')?.value || '').length > 0`, 25000, "claude replies");
  await sleep(1000);
  const claudeReply = await c1.evaljs(`(() => ({
    speaker: document.querySelector('#character')?.textContent?.trim() || '',
    line: document.querySelector('#inputMessage')?.value || '',
  }))()`);
  check("Claude interactable (player can talk to Claude)", claudeReply.speaker.toLowerCase().includes('claude') && claudeReply.line.length > 0, `speaker=${claudeReply.speaker} line="${claudeReply.line.slice(0,30)}"`);

  // ── 5. Narrative Event committed (backend truth) ──
  const state = await (await fetch(`${API}/api/game/state?session_id=${sessionId}`)).json();
  const evCommitted = state.presentation_state?.characters?.some(c => c.character_id === 'claude');
  check("Narrative Event committed (backend state has claude)", !!evCommitted, `chars=${JSON.stringify(state.presentation_state?.characters?.map(c=>c.character_id))}`);
  const history = await (await fetch(`${API}/api/chat/history?session_id=${sessionId}`)).json();
  const hasClaudeLine = history.messages?.some(m => m.character_id === 'claude' && m.content);
  check("Claude line in session history", !!hasClaudeLine, "");

  // ── 6. Session restore after refresh ──
  // 模拟刷新：同一 Chrome 页面 reload（localStorage 保留 session_id）
  const c2 = c1;
  await c2.send("Page.reload", { ignoreCache: true });
  await waitFor(c2.evaljs, `document.querySelector('#inputMessage') !== null`, 20000, "dialog remount");
  await waitFor(c2.evaljs, `localStorage.getItem('gal_session_id') === ${JSON.stringify(sessionId)}`, 8000, "same session");
  await sleep(2000);
  const restored = await c2.evaljs(`(() => {
    const claudeImg = Array.from(document.querySelectorAll('img')).find(i => (i.currentSrc || i.src || '').includes('claude-main'));
    const line = document.querySelector('#inputMessage')?.value || '';
    const char = document.querySelector('#character')?.textContent?.trim() || '';
    return { claudeVisible: !!claudeImg && claudeImg.naturalWidth > 0, line, char, sid: localStorage.getItem('gal_session_id') };
  })()`);
  check("Refresh restores same session_id", restored.sid === sessionId, "");
  check("Refresh restores Claude on stage", !!restored.claudeVisible, "");
  check("Refresh restores last dialogue", restored.line.length > 0, `char=${restored.char} line="${restored.line.slice(0,30)}"`);

  c1.ws.close(); c1.chrome.kill();
  for (let i=0;i<5;i++){ try { const { rmSync } = await import("node:fs"); rmSync(PROFILE,{recursive:true,force:true}); break; } catch { await sleep(800); } }

  const failed = results.filter(r => !r.ok);
  console.log(`\n=== Task 4 summary: ${results.length - failed.length}/${results.length} PASS ===`);
  if (failed.length) { console.log("FAILED:"); failed.forEach(f => console.log(" - " + f.name)); process.exit(1); }
}

main().catch(e => { console.error("FATAL:", e.message); process.exit(1); });
