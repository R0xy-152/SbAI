"""内部运营看板页面（docs/21 §5）。

单文件 HTML + 原生 JS，无构建、无图表库；token 从 URL ?token= 读取并附到
每个数据请求头。数据端点本身也有 GAL_OPS_TOKEN 门禁，页面只是展示层。
"""

PAGE_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>gal 运营看板（内部）</title>
<style>
  body { font-family: system-ui, -apple-system, "PingFang SC", sans-serif;
         margin: 0; background: #f5f6f8; color: #1f2329; }
  header { padding: 16px 24px; background: #fff; border-bottom: 1px solid #e5e6e8;
           display: flex; justify-content: space-between; align-items: center; }
  header h1 { font-size: 18px; margin: 0; }
  .note { font-size: 12px; color: #8a919f; }
  main { padding: 20px 24px; max-width: 1080px; margin: 0 auto; }
  section { background: #fff; border: 1px solid #e5e6e8; border-radius: 8px;
            padding: 16px 20px; margin-bottom: 16px; }
  section h2 { font-size: 15px; margin: 0 0 12px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #f0f1f3; }
  th { color: #8a919f; font-weight: 500; }
  .bar-row { display: flex; align-items: center; gap: 10px; margin: 6px 0; font-size: 13px; }
  .bar-label { width: 180px; text-align: right; color: #4e5665; }
  .bar-track { flex: 1; background: #f0f1f3; border-radius: 4px; height: 18px; }
  .bar-fill { background: #3b82f6; border-radius: 4px; height: 18px; min-width: 2px; }
  .bar-num { width: 90px; font-variant-numeric: tabular-nums; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
  .card { border: 1px solid #e5e6e8; border-radius: 8px; padding: 10px 12px; }
  .card .k { font-size: 12px; color: #8a919f; }
  .card .v { font-size: 20px; font-weight: 600; margin-top: 4px; }
  .error { color: #d54941; font-size: 13px; }
</style>
</head>
<body>
<header>
  <h1>gal 运营看板（内部）</h1>
  <span class="note">事件口径见 docs/21；样本小时数字仅作管线演示，不作为统计结论</span>
</header>
<main>
  <section id="funnel"><h2>序章完成漏斗</h2><div id="funnel-body">加载中…</div></section>
  <section id="prefs"><h2>角色偏好</h2><div id="prefs-body">加载中…</div></section>
  <section id="ai"><h2>AI 对话指标</h2><div id="ai-body">加载中…</div></section>
  <section id="fb"><h2>玩家反馈（留言 + 分类 + 抽检）</h2><div id="fb-body">加载中…</div></section>
</main>
<script>
const params = new URLSearchParams(location.search);
const token = params.get("token") || "";
const headers = token ? {"x-ops-token": token} : {};
async function get(url) {
  const res = await fetch(url, {headers});
  if (!res.ok) throw new Error(url + " -> " + res.status);
  return res.json();
}
function el(html) { const d = document.createElement("div"); d.innerHTML = html; return d.firstElementChild; }

(async () => {
  try {
    const funnel = await get("/api/ops/funnel");
    const max = Math.max(1, ...Object.values(funnel.stage_counts));
    const labels = {
      started: "开始序章", visit_chosen: "≥1 次访问选择",
      visit_completed: "≥1 篇角色篇完成", three_visits: "三篇全部完成",
      prologue_completed: "序章完成", ai_chat_entered: "进入 AI 对话",
    };
    document.getElementById("funnel-body").replaceChildren(
      ...Object.entries(funnel.stage_counts).map(([k, v]) => el(
        '<div class="bar-row"><span class="bar-label">' + labels[k] + '</span>' +
        '<div class="bar-track"><div class="bar-fill" style="width:' +
        (100 * v / max) + '%"></div></div><span class="bar-num">' + v + '</span></div>'
      )),
      el('<table><tr><th>角色</th><th>访问选择</th><th>篇完成</th><th>完成率</th></tr>' +
        Object.entries(funnel.characters).map(([c, d]) =>
          '<tr><td>' + c + '</td><td>' + d.chosen + '</td><td>' + d.completed +
          '</td><td>' + (d.completion_rate === null ? '—' : (100 * d.completion_rate).toFixed(0) + '%') + '</td></tr>'
        ).join('') + '</table>')
    );

    const prefs = await get("/api/ops/preferences");
    const fmt = (obj) => Object.entries(obj).map(([k, v]) => k + ': ' + v).join('，') || '—';
    document.getElementById("prefs-body").replaceChildren(el(
      '<table><tr><th>首访角色</th><td>' + fmt(prefs.first_visit) + '</td></tr>' +
      '<tr><th>聊天角色选择</th><td>' + fmt(prefs.chat_choice) + '</td></tr></table>'
    ));

    const ai = await get("/api/ops/ai");
    document.getElementById("ai-body").replaceChildren(el(
      '<div class="cards">' +
      '<div class="card"><div class="k">AI 成功率（turn/(turn+error)）</div><div class="v">' +
        (ai.success_rate === null ? '—' : (100 * ai.success_rate).toFixed(1) + '%') + '</div></div>' +
      '<div class="card"><div class="k">延迟 P50</div><div class="v">' +
        (ai.latency.p50_ms === null ? '—' : ai.latency.p50_ms.toFixed(0) + ' ms') + '</div></div>' +
      '<div class="card"><div class="k">延迟 P95（n=' + ai.latency.n + '）</div><div class="v">' +
        (ai.latency.p95_ms === null ? '—' : ai.latency.p95_ms.toFixed(0) + ' ms') + '</div></div>' +
      '<div class="card"><div class="k">总成本</div><div class="v">¥' + ai.cost.total_cny.toFixed(4) + '</div></div>' +
      '<div class="card"><div class="k">单次完整体验平均成本</div><div class="v">' +
        (ai.cost.avg_per_complete_session_cny === null ? '—' : '¥' + ai.cost.avg_per_complete_session_cny.toFixed(4)) + '</div></div>' +
      '<div class="card"><div class="k">校验拦截</div><div class="v">' + ai.validation_reject_count + '</div></div>' +
      '</div>'
    ));

    const fb = await get("/api/ops/feedback");
    const p = fb.precision;
    const notesRows = fb.notes.map((n) => {
      const a = fb.analyses.find((x) => x.note_key === n.note_key);
      return '<tr><td>' + n.display_name + '</td><td>' + (n.character_id || '') + '</td>' +
        '<td>' + n.content.replace(/[<>&]/g, (m) => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[m])) + '</td>' +
        '<td>' + (a ? (a.topic + ' / ' + a.severity + (a.is_duplicate_of ? '（重复）' : '')) : '未分类') + '</td></tr>';
    }).join('');
    document.getElementById("fb-body").replaceChildren(el(
      '<div class="cards"><div class="card"><div class="k">留言总数</div><div class="v">' +
        fb.notes.length + '</div></div>' +
      '<div class="card"><div class="k">分类数</div><div class="v">' + fb.analyses.length + '</div></div>' +
      '<div class="card"><div class="k">抽检 Precision（topic，n=' + p.n + '）</div><div class="v">' +
        (p.topic.precision === null ? '—' : (100 * p.topic.precision).toFixed(0) + '%') + '</div></div>' +
      '<div class="card"><div class="k">抽检 Precision（severity）</div><div class="v">' +
        (p.severity.precision === null ? '—' : (100 * p.severity.precision).toFixed(0) + '%') + '</div></div></div>' +
      '<table><tr><th>玩家</th><th>角色</th><th>留言</th><th>分类</th></tr>' + notesRows + '</table>'
    ));
  } catch (err) {
    document.body.insertAdjacentHTML("beforeend",
      '<div class="error">加载失败：' + err.message + '（需要 ?token=GAL_OPS_TOKEN）</div>');
  }
})();
</script>
</body>
</html>
"""
