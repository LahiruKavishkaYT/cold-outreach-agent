#!/usr/bin/env python3
"""Build a self-contained HTML dashboard from the lead index.

Reads:
  state/leads-index.json     (authoritative per-lead state)
  state/draft/<id>.json       (subject/body/evidence/assumptions, when present)
  data/approvals.log          (append-only approval trail)

Writes:
  outputs/dashboard.html      (open directly in a browser; no server needed)

Re-run after any state change to refresh:  python scripts/build_dashboard.py
"""
import json
import os
import html
from datetime import datetime, timezone

ROOT = os.environ.get("OUTREACH_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "state", "leads-index.json")
DRAFT_DIR = os.path.join(ROOT, "state", "draft")
APPROVALS = os.path.join(ROOT, "data", "approvals.log")
OUT = os.path.join(ROOT, "outputs", "dashboard.html")

# Display order + colors for known states.
STATE_META = {
    "scheduled":         ("Scheduled", "#2563eb"),
    "saved_as_draft":    ("Saved as draft", "#0891b2"),
    "approved_for_draft":("Approved", "#0891b2"),
    "awaiting_review":   ("Awaiting review", "#d97706"),
    "awaiting_final_approval": ("Awaiting approval", "#d97706"),
    "sent_by_user":      ("Sent", "#16a34a"),
    "reply_received":    ("Reply received", "#7c3aed"),
    "research_blocked":  ("Research blocked", "#9ca3af"),
    "no_email":          ("No email", "#9ca3af"),
    "skipped_has_chat":  ("Skipped (has chat)", "#9ca3af"),
    "cancelled":         ("Cancelled", "#6b7280"),
    "expired":           ("Expired", "#dc2626"),
}


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def approval_map():
    """lead_id -> latest approval text/timestamp from the append-only log."""
    out = {}
    try:
        with open(APPROVALS, "r", encoding="utf-8") as fh:
            for line in fh:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 5:
                    ts, lead, ver, h, text = parts[0], parts[1], parts[2], parts[3], parts[4]
                    out[lead] = {"ts": ts, "version": ver, "hash": h, "text": text}
    except FileNotFoundError:
        pass
    return out


def main():
    index = load_json(INDEX, {}) or {}
    # v3 fix: log_update.py writes a flat {lead_id: record} index, but v2 read
    # index["leads"] (the old side-index shape), so the dashboard showed 0 leads.
    leads = index["leads"] if isinstance(index.get("leads"), dict) else \
        {k: v for k, v in index.items() if isinstance(v, dict)}
    approvals = approval_map()

    rows = []
    for lead_id, info in leads.items():
        draft = load_json(os.path.join(DRAFT_DIR, lead_id + ".json"), {}) or {}
        ap = approvals.get(lead_id, {})
        rows.append({
            "lead_id": lead_id,
            "company": info.get("company_name") or info.get("company") or draft.get("company_name") or lead_id,
            "row": info.get("csv_row"),
            "recipient": info.get("recipient"),
            "location": info.get("location", ""),
            "state": info.get("state", "unknown"),
            "version": info.get("email_version"),
            "approved_date": info.get("approved_date") or draft.get("approved_date"),
            "expiry": info.get("approval_expiry_date") or draft.get("approval_expiry_date"),
            "scheduled": info.get("scheduled_send_at"),
            "sent_date": info.get("sent_date") or draft.get("sent_date"),
            "note": info.get("note", ""),
            "subject": draft.get("subject", ""),
            "body": draft.get("body", ""),
            "evidence": draft.get("personalization_evidence", []),
            "assumptions": draft.get("unverified_assumptions", []),
            "approval_text": ap.get("text", ""),
            "approval_ts": ap.get("ts", ""),
            "approved_hash": (info.get("approved_hash") or draft.get("approved_hash") or "")[:12],
        })

    rows.sort(key=lambda r: (r["row"] is None, r["row"] or 0))

    # counts
    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "generated": generated,
        "campaign": index.get("campaign_id", ""),
        "scheduled_local": index.get("scheduled_send_local", ""),
        "rows": rows,
        "counts": counts,
        "state_meta": STATE_META,
    }
    data_json = json.dumps(payload, ensure_ascii=False)

    # Inside a <script type="application/json"> block we must NOT HTML-escape;
    # only neutralize a literal </script> sequence so the block can't be closed early.
    htmlpage = HTML_TEMPLATE.replace("/*DATA*/", data_json.replace("</", "<\\/"))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(htmlpage)
    print("Wrote {} ({} leads)".format(OUT, len(rows)))
    print("Open it in a browser: file:///{}".format(OUT.replace(os.sep, "/")))


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Outreach Studio — Lead Dashboard</title>
<style>
  :root{ --bg:#0f172a; --card:#1e293b; --muted:#94a3b8; --line:#334155; --text:#e2e8f0; }
  *{ box-sizing:border-box; }
  body{ margin:0; font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
        background:var(--bg); color:var(--text); }
  header{ padding:20px 24px; border-bottom:1px solid var(--line); }
  h1{ margin:0 0 4px; font-size:20px; }
  .sub{ color:var(--muted); font-size:13px; }
  .wrap{ padding:18px 24px; }
  .cards{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:16px; }
  .card{ background:var(--card); border:1px solid var(--line); border-radius:10px;
         padding:10px 14px; min-width:120px; cursor:pointer; user-select:none; }
  .card:hover{ border-color:#64748b; }
  .card.active{ outline:2px solid #3b82f6; }
  .card .n{ font-size:22px; font-weight:700; }
  .card .l{ font-size:12px; color:var(--muted); }
  .controls{ display:flex; gap:10px; margin-bottom:12px; flex-wrap:wrap; }
  input[type=search]{ flex:1; min-width:220px; background:var(--card); border:1px solid var(--line);
        color:var(--text); padding:9px 12px; border-radius:8px; font-size:14px; }
  table{ width:100%; border-collapse:collapse; background:var(--card);
         border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  th,td{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--line); vertical-align:top; }
  th{ font-size:12px; text-transform:uppercase; letter-spacing:.03em; color:var(--muted);
      cursor:pointer; white-space:nowrap; }
  tr.lead{ cursor:pointer; }
  tr.lead:hover{ background:#243049; }
  .badge{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:12px;
          font-weight:600; color:#fff; white-space:nowrap; }
  .mono{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; color:var(--muted); }
  .detail{ background:#16203a; }
  .detail td{ padding:0; }
  .detailinner{ padding:16px 18px; }
  .email{ background:#0b1324; border:1px solid var(--line); border-radius:8px;
          padding:14px 16px; white-space:pre-wrap; max-width:760px; }
  .email .subj{ font-weight:700; margin-bottom:8px; }
  .kv{ color:var(--muted); font-size:12px; margin:2px 0; }
  ul{ margin:6px 0 0; padding-left:18px; }
  li{ margin:2px 0; }
  .sec{ margin-top:12px; font-size:12px; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); }
  a{ color:#60a5fa; }
  .hidden{ display:none; }
  .note{ color:#fbbf24; font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>Outreach Studio — Lead Dashboard</h1>
  <div class="sub" id="sub"></div>
</header>
<div class="wrap">
  <div class="cards" id="cards"></div>
  <div class="controls">
    <input type="search" id="q" placeholder="Search company, email, location, state…">
  </div>
  <table id="tbl">
    <thead><tr>
      <th data-k="row">#</th>
      <th data-k="company">Company</th>
      <th data-k="state">Status</th>
      <th data-k="recipient">Recipient</th>
      <th data-k="location">Location</th>
      <th data-k="scheduled">Scheduled</th>
      <th data-k="expiry">Expires</th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table>
</div>
<script id="data" type="application/json">/*DATA*/</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const META = D.state_meta;
let filter = null, q = "", sortK = "row", sortAsc = true;

document.getElementById('sub').textContent =
  `Campaign ${D.campaign || '—'} · ${D.rows.length} leads · scheduled ${D.scheduled_local || '—'} · generated ${D.generated}`;

function badge(state){
  const m = META[state] || [state, '#6b7280'];
  return `<span class="badge" style="background:${m[1]}">${m[0]}</span>`;
}
function esc(s){ return (s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

function renderCards(){
  const c = document.getElementById('cards');
  const order = Object.keys(META).filter(k=>D.counts[k]);
  let h = `<div class="card ${filter===null?'active':''}" data-s=""><div class="n">${D.rows.length}</div><div class="l">All</div></div>`;
  for(const k of order){
    h += `<div class="card ${filter===k?'active':''}" data-s="${k}"><div class="n">${D.counts[k]}</div><div class="l">${META[k][0]}</div></div>`;
  }
  c.innerHTML = h;
  c.querySelectorAll('.card').forEach(el=>el.onclick=()=>{
    filter = el.dataset.s || null; renderCards(); renderRows();
  });
}

function visible(){
  let rows = D.rows.slice();
  if(filter) rows = rows.filter(r=>r.state===filter);
  if(q){ const t=q.toLowerCase();
    rows = rows.filter(r=>[r.company,r.recipient,r.location,r.state,r.subject].join(' ').toLowerCase().includes(t)); }
  rows.sort((a,b)=>{
    let x=a[sortK], y=b[sortK];
    if(x==null)x=''; if(y==null)y='';
    if(typeof x==='number'||typeof y==='number'){ x=+x||0; y=+y||0; }
    return (x<y?-1:x>y?1:0)*(sortAsc?1:-1);
  });
  return rows;
}

function detail(r){
  const ev = (r.evidence||[]).map(e=>`<li>${esc(e.fact)} ${e.source?`<a href="${esc(e.source)}" target="_blank">src</a>`:''}</li>`).join('');
  const as = (r.assumptions||[]).map(a=>`<li>${esc(a)}</li>`).join('');
  const email = r.subject||r.body ?
    `<div class="email"><div class="subj">${esc(r.subject)}</div>${esc(r.body)}</div>` :
    `<div class="note">No draft written for this lead.</div>`;
  return `<div class="detailinner">
    ${email}
    <div class="kv">Lead id: <span class="mono">${esc(r.lead_id)}</span> · CSV row ${esc(r.row)} · version ${esc(r.version)||'—'}</div>
    ${r.approved_hash?`<div class="kv">Approved hash: <span class="mono">${esc(r.approved_hash)}…</span> · approved ${esc(r.approved_date)||'—'} · expires ${esc(r.expiry)||'—'}</div>`:''}
    ${r.approval_text?`<div class="kv">Approval: “${esc(r.approval_text)}” <span class="mono">(${esc(r.approval_ts)})</span></div>`:''}
    ${r.scheduled?`<div class="kv">Scheduled send: <span class="mono">${esc(r.scheduled)}</span> (the operator, manual Gmail)</div>`:''}
    ${r.note?`<div class="note">⚠ ${esc(r.note)}</div>`:''}
    ${ev?`<div class="sec">Personalization evidence</div><ul>${ev}</ul>`:''}
    ${as?`<div class="sec">Unverified assumptions</div><ul>${as}</ul>`:''}
  </div>`;
}

function renderRows(){
  const tb = document.getElementById('rows');
  const rows = visible();
  let h='';
  rows.forEach((r,i)=>{
    h += `<tr class="lead" data-i="${i}">
      <td class="mono">${esc(r.row)}</td>
      <td><strong>${esc(r.company)}</strong></td>
      <td>${badge(r.state)}</td>
      <td class="mono">${esc(r.recipient)||'—'}</td>
      <td>${esc(r.location)||'—'}</td>
      <td class="mono">${r.scheduled?esc(r.scheduled.replace('T',' ').replace(':00Z',' UTC')):'—'}</td>
      <td class="mono">${esc(r.expiry)||'—'}</td>
    </tr>
    <tr class="detail hidden" id="d${i}"><td colspan="7">${detail(r)}</td></tr>`;
  });
  tb.innerHTML = h || `<tr><td colspan="7" style="color:var(--muted)">No leads match.</td></tr>`;
  tb.querySelectorAll('tr.lead').forEach(tr=>tr.onclick=()=>{
    document.getElementById('d'+tr.dataset.i).classList.toggle('hidden');
  });
}

document.getElementById('q').oninput = e=>{ q=e.target.value; renderRows(); };
document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{
  const k=th.dataset.k; if(sortK===k) sortAsc=!sortAsc; else {sortK=k; sortAsc=true;} renderRows();
});
renderCards(); renderRows();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
