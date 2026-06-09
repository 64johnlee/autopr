"""AutoPR FastAPI dashboard — live activity feed + stats."""
from __future__ import annotations

import asyncio
import json
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

load_dotenv()

app = FastAPI(title="AutoPR", description="Autonomous bounty PR agent", version="0.1.0")

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>AutoPR — Autonomous Bounty Agent</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,monospace;
         background:#0d1117;color:#e6edf3;min-height:100vh}
    header{background:linear-gradient(135deg,#1a1f2e,#161b27);
           border-bottom:1px solid #30363d;padding:1.5rem 2rem}
    header h1{font-size:1.8rem;font-weight:700;color:#58a6ff}
    header p{color:#8b949e;margin-top:.3rem}
    .badge{background:#238636;color:#fff;border-radius:12px;
           padding:.2rem .7rem;font-size:.75rem;font-weight:600;margin-left:.5rem}
    main{max-width:1100px;margin:0 auto;padding:2rem}
    .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:2rem}
    .stat{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1rem;text-align:center}
    .stat .val{font-size:2rem;font-weight:700;color:#58a6ff}
    .stat .label{font-size:.8rem;color:#8b949e;margin-top:.25rem}
    .stat.earned .val{color:#3fb950}
    .panel{background:#161b22;border:1px solid #30363d;border-radius:8px;margin-bottom:1.5rem}
    .panel-header{padding:.75rem 1rem;border-bottom:1px solid #30363d;
                  font-size:.85rem;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.05em}
    #feed{height:420px;overflow-y:auto;padding:.75rem 1rem;font-family:monospace;font-size:.82rem}
    .event{padding:.2rem 0;border-bottom:1px solid #161b22;line-height:1.4}
    .event .ts{color:#484f58;margin-right:.5rem}
    .event.pr_opened .msg{color:#3fb950;font-weight:600}
    .event.coding_start .msg{color:#58a6ff}
    .event.error .msg, .event.pr_fail .msg, .event.coding_fail .msg{color:#f85149}
    .event.triage_skip .msg{color:#8b949e}
    .event.scan_done .msg{color:#d29922}
    #current{padding:.75rem 1rem;min-height:3rem;font-size:.9rem;color:#e6edf3}
    .pr-list{padding:.5rem 1rem}
    .pr-item{display:flex;align-items:center;gap:.75rem;padding:.5rem 0;
             border-bottom:1px solid #21262d;font-size:.85rem}
    .pr-item:last-child{border-bottom:none}
    .pr-item .amount{color:#3fb950;font-weight:600;min-width:3.5rem}
    .pr-item a{color:#58a6ff;text-decoration:none}
    .pr-item a:hover{text-decoration:underline}
    .dot{width:8px;height:8px;border-radius:50%;background:#3fb950;
         animation:pulse 2s infinite}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  </style>
</head>
<body>
<header>
  <h1>AutoPR <span class="badge">LIVE</span></h1>
  <p>Autonomous open-source bounty agent · Qwen on Alibaba Cloud · <span id="uptime">starting…</span></p>
</header>
<main>
  <div class="stats">
    <div class="stat"><div class="val" id="s-attempts">0</div><div class="label">Attempts</div></div>
    <div class="stat"><div class="val" id="s-prs">0</div><div class="label">PRs Open</div></div>
    <div class="stat"><div class="val" id="s-merged">0</div><div class="label">Merged</div></div>
    <div class="stat earned"><div class="val" id="s-earned">$0</div><div class="label">Earned</div></div>
    <div class="stat"><div class="val" id="s-rate">—</div><div class="label">Merge Rate</div></div>
  </div>

  <div class="panel">
    <div class="panel-header"><span class="dot" style="display:inline-block;vertical-align:middle;margin-right:.5rem"></span>Live Activity</div>
    <div id="current">(waiting for agent…)</div>
    <div id="feed"></div>
  </div>

  <div class="panel">
    <div class="panel-header">Recent PRs</div>
    <div class="pr-list" id="pr-list"><div style="padding:.5rem;color:#8b949e;font-size:.85rem">(no PRs yet)</div></div>
  </div>
</main>
<script>
const feed    = document.getElementById('feed');
const current = document.getElementById('current');
const prList  = document.getElementById('pr-list');
const prs     = [];
let stats     = {total_attempts:0, total_earned:0, by_status:{}};
const start   = Date.now();

function updateStats() {
  const bs = stats.by_status || {};
  document.getElementById('s-attempts').textContent = stats.total_attempts || 0;
  const prOpen = (bs.pr_open||{}).count||0;
  document.getElementById('s-prs').textContent = prOpen;
  const merged = (bs.merged||{}).count||0;
  document.getElementById('s-merged').textContent = merged;
  document.getElementById('s-earned').textContent = '$' + (stats.total_earned||0).toFixed(0);
  const rate = stats.total_attempts > 0 ? (merged / stats.total_attempts * 100).toFixed(0)+'%' : '—';
  document.getElementById('s-rate').textContent = rate;
  const mins = Math.floor((Date.now()-start)/60000);
  document.getElementById('uptime').textContent = `running ${mins}m`;
}

function addEvent(evt) {
  const ts  = evt.ts ? new Date(evt.ts).toLocaleTimeString() : '';
  const kind = evt.kind || '';
  const d   = evt.data || {};
  let msg   = '';

  if      (kind==='agent')        msg = '🤖 ' + d.msg;
  else if (kind==='scan_done')    msg = `🔍 scanned ${d.count} issues — top: ${(d.top||[]).map(i=>`${i.key} $${i.amount}`).join(', ')}`;
  else if (kind==='triage_start') msg = `⚖️  triaging ${d.issue} — ${d.title} ($${d.amount})`;
  else if (kind==='triage_skip')  msg = `⏭  skipped ${d.issue}: ${d.reason}`;
  else if (kind==='coding_start') msg = `💻 coding ${d.issue}: ${d.approach}`;
  else if (kind==='coder_event')  msg = `   ${d.msg}`;
  else if (kind==='coding_fail')  msg = `❌ coding failed ${d.issue}: ${d.error}`;
  else if (kind==='submitting')   msg = `📤 submitting PR for ${d.issue} (${(d.files||[]).length} files)`;
  else if (kind==='pr_opened')  { msg = `✅ PR opened! ${d.issue} → ${d.pr_url} ($${d.amount})`; addPR(d); }
  else if (kind==='pr_fail')      msg = `❌ PR failed ${d.issue}: ${d.error}`;
  else if (kind==='cycle_done') { msg = `♻️  cycle complete`; stats=d; updateStats(); }
  else if (kind==='error')        msg = `🔥 error: ${d.msg}`;
  else return;

  const div = document.createElement('div');
  div.className = `event ${kind}`;
  div.innerHTML = `<span class="ts">${ts}</span><span class="msg">${escHtml(msg)}</span>`;
  feed.prepend(div);
  if (feed.children.length > 200) feed.removeChild(feed.lastChild);

  if (kind==='coding_start') current.textContent = `Working on: ${d.issue} — ${d.approach||''}`;
  if (kind==='pr_opened')    current.textContent = `PR submitted: ${d.issue} → ${d.pr_url}`;
  if (kind==='cycle_done')   current.textContent = `Idle — next scan in ~15 min`;
}

function addPR(d) {
  prs.unshift(d);
  if (prList.querySelector('[style]')) prList.innerHTML = '';
  const item = document.createElement('div');
  item.className = 'pr-item';
  item.innerHTML = `<span class="amount">$${d.amount}</span><a href="${escHtml(d.pr_url)}" target="_blank">${escHtml(d.issue)}</a>`;
  prList.prepend(item);
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

const es = new EventSource('/stream');
es.onmessage = e => { try { addEvent(JSON.parse(e.data)); } catch {} };
es.onerror   = () => { current.textContent = 'connection lost — retrying…'; };

setInterval(updateStats, 60000);
updateStats();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> str:
    return _HTML


@app.get("/stream")
async def stream():
    from autopr import events

    async def generator():
        q = events.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30)
                    yield {"data": json.dumps(event)}
                except asyncio.TimeoutError:
                    yield {"data": json.dumps({"kind": "ping"})}
        except asyncio.CancelledError:
            events.unsubscribe(q)

    return EventSourceResponse(generator())


@app.get("/stats")
async def stats_endpoint():
    from autopr.memory import stats, recent_attempts
    return {"stats": stats(), "recent": recent_attempts(10)}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "autopr"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
