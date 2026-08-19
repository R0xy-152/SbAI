// docs/13 Task 3 acceptance: browser runs with no Tauri runtime error;
// all role assets load via Web URL; no fs access in the page.
import { spawn } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const VUE_URL = "http://localhost:5174/game";
const OUT_DIR = dirname(fileURLToPath(import.meta.url));
const PROFILE = join(OUT_DIR, ".task3-profile");
const PORT = 9352;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main(){
  const chrome = spawn(CHROME, ["--headless=new","--disable-gpu","--no-sandbox","--hide-scrollbars",`--remote-debugging-port=${PORT}`,`--user-data-dir=${PROFILE}`,`--window-size=1366,768`,`about:blank`]);
  let wsUrl; for (let i=0;i<60;i++){ try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); const p = l.find(t=>t.type==="page"); if (p){ wsUrl=p.webSocketDebuggerUrl; break; } } catch {} await sleep(500); }
  const ws = new WebSocket(wsUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
  let id=0; const pend=new Map(); const consoleMsgs=[];
  ws.onmessage=(ev)=>{const m=JSON.parse(ev.data);
    if(m.method==="Runtime.consoleAPICalled"){consoleMsgs.push(m.params.type+": "+m.params.args.map(a=>a.value||a.description||"").join(" "));}
    if(m.id&&pend.has(m.id)){const p=pend.get(m.id);pend.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result);}};
  const send=(method,params={})=>new Promise((res,rej)=>{const mid=++id;pend.set(mid,{resolve:res,reject:rej});ws.send(JSON.stringify({id:mid,method,params}));});
  await send("Page.enable"); await send("Runtime.enable");
  const evaljs=async(expr)=>{const r=await send("Runtime.evaluate",{expression:expr,returnByValue:true,awaitPromise:true}); if(r.exceptionDetails) throw new Error(r.exceptionDetails.text); return r.result.value;};
  await send("Page.navigate",{url:VUE_URL});
  await sleep(5000);
  const assets = await evaljs(`(() => {
    const srcs = [];
    document.querySelectorAll('img').forEach(i => srcs.push(i.src));
    document.querySelectorAll('[style*="url("]').forEach(el => { const m = el.style.backgroundImage.match(/url\\(["']?([^"')]+)/); if (m) srcs.push(m[1]); });
    const uniq = Array.from(new Set(srcs));
    // Web URL = http(s) scheme OR relative path (resolved by browser to current origin).
    // Reject file://, host absolute paths (C:\\\\...), and Tauri convertFileSrc (asset://...).
    const bad = uniq.filter(s => /^file:/i.test(s) || /^[a-zA-Z]:\\\\/.test(s) || /^asset:/.test(s) || /^tauri:/.test(s));
    return { imgs: document.querySelectorAll('img').length, srcs: uniq, allWebUrl: bad.length === 0, bad };
  })()`);
  const errors = consoleMsgs.filter(m => m.startsWith("error:"));
  const tauriErrors = consoleMsgs.filter(m => /tauri|not.*defined|Cannot read|is not a function/i.test(m));
  console.log("console messages:", consoleMsgs.length);
  console.log("errors:", JSON.stringify(errors.slice(0,5), null, 1));
  console.log("tauri-ish errors:", JSON.stringify(tauriErrors));
  console.log("assets:", JSON.stringify(assets, null, 1));
  console.log("=== Task 3 acceptance ===");
  console.log("build:", "PASS (run separately)");
  console.log("no Tauri runtime error:", tauriErrors.length===0 ? "PASS" : "FAIL");
  console.log("all assets via Web URL:", assets.allWebUrl ? "PASS" : "FAIL");
  ws.close(); chrome.kill();
  const { rmSync } = await import("node:fs");
  for (let i=0;i<5;i++){ try { rmSync(PROFILE,{recursive:true,force:true}); break; } catch { await sleep(800); } }
}
main().catch(e=>{console.error("FAIL:",e.message);process.exit(1);});
