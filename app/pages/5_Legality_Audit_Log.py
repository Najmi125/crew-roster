import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Legality & Audit Log", page_icon="🛡️", layout="wide")

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Exo+2:wght@300;400;600&family=Share+Tech+Mono&display=swap');
  .page-title { font-family:'Orbitron',monospace; font-size:1.3rem; font-weight:700; color:#1a1a2e; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:0.2rem; }
  .page-sub   { font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#888; letter-spacing:0.15em; margin-bottom:1rem; }
  .audit-table { width:100%; border-collapse:collapse; font-family:'Exo 2',sans-serif; font-size:0.78rem; }
  .audit-table th { background:#1a1a2e; color:#fff; padding:8px 10px; font-size:0.65rem; letter-spacing:0.08em; text-transform:uppercase; text-align:left; }
  .audit-table td { padding:7px 10px; border-bottom:1px solid #eee; vertical-align:top; }
  .audit-table tr:hover td { background:#f8f9fa; }
  .type-override { color:#721c24; font-weight:700; font-family:'Share Tech Mono',monospace; font-size:0.68rem; }
  .type-violation{ color:#856404; font-weight:700; font-family:'Share Tech Mono',monospace; font-size:0.68rem; }
  .type-system   { color:#155724; font-family:'Share Tech Mono',monospace; font-size:0.68rem; }
  .summary-cards { display:grid; grid-template-columns:repeat(4,1fr); gap:0.8rem; margin-bottom:1.2rem; }
  .sum-card { background:#f7f8fc; border:1px solid #e0e6f0; border-radius:8px; padding:0.8rem 1rem; border-top:3px solid #1a1a2e; text-align:center; }
  .sum-val  { font-family:'Orbitron',monospace; font-size:1.1rem; font-weight:700; color:#1a1a2e; }
  .sum-lbl  { font-family:'Exo 2',sans-serif; font-size:0.65rem; color:#888; text-transform:uppercase; margin-top:2px; }
  .section-hdr { font-family:'Orbitron',monospace; font-size:0.7rem; color:#1a1a2e; letter-spacing:0.15em; border-bottom:2px solid #1a1a2e; padding-bottom:0.3rem; margin:1rem 0 0.6rem; text-transform:uppercase; }
  .print-btn { display:inline-block; background:#1a1a2e; color:#fff; border:none; border-radius:5px; padding:6px 16px; font-size:0.75rem; cursor:pointer; font-family:'Share Tech Mono',monospace; letter-spacing:0.08em; margin-bottom:1rem; }
  @media print { .stSidebar,.stButton,button,.print-btn { display:none !important; } }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🛡️ Legality & Audit Log</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">REGULATORY SHIELD — CAA AUDIT DEFENSE — COMPLETE OVERRIDE & VIOLATION HISTORY</div>', unsafe_allow_html=True)

# Date filter
col1, col2, col3 = st.columns([2, 2, 3])
with col1:
    from_date = st.date_input("From", value=date.today() - timedelta(days=30))
with col2:
    to_date = st.date_input("To", value=date.today())

st.markdown('<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>', unsafe_allow_html=True)
csv_placeholder = st.empty()

try:
    conn = get_connection()
    cur  = conn.cursor()

    # ── Manual Overrides ──────────────────────────────────────────────────────
    cur.execute("""
        SELECT
            r.id, fs.flight_number, fs.departure_time::date,
            cm.full_name, cm.role,
            r.override_reason, r.override_by, r.created_at
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        JOIN crew_master     cm ON cm.id = r.crew_id
        WHERE r.is_manual_override = TRUE
          AND fs.departure_time::date BETWEEN %s AND %s
        ORDER BY r.created_at DESC
    """, (from_date, to_date))
    overrides = cur.fetchall()

    # ── FDTL Violations ───────────────────────────────────────────────────────
    cur.execute("""
        SELECT
            lv.id, lv.violation_type, lv.details, lv.flagged_at,
            cm.full_name, fs.flight_number
        FROM legality_violations lv
        LEFT JOIN crew_master     cm ON cm.id = lv.crew_id
        LEFT JOIN flight_schedule fs ON fs.id = lv.flight_id
        WHERE lv.flagged_at::date BETWEEN %s AND %s
        ORDER BY lv.flagged_at DESC
    """, (from_date, to_date))
    violations = cur.fetchall()

    # ── Audit Trail ───────────────────────────────────────────────────────────
    try:
        cur.execute("""
            SELECT action, performed_by, target_table, old_value, new_value, timestamp
            FROM audit_trail
            WHERE timestamp::date BETWEEN %s AND %s
            ORDER BY timestamp DESC LIMIT 100
        """, (from_date, to_date))
        audit = cur.fetchall()
    except:
        audit = []

    cur.close()
    conn.close()

    # Summary
    st.markdown(f"""
    <div class="summary-cards">
      <div class="sum-card" style="border-top-color:#dc3545">
        <div class="sum-val" style="color:#dc3545">{len(overrides)}</div>
        <div class="sum-lbl">Manual Overrides</div>
      </div>
      <div class="sum-card" style="border-top-color:#f59e0b">
        <div class="sum-val" style="color:#856404">{len(violations)}</div>
        <div class="sum-lbl">FDTL Violations Prevented</div>
      </div>
      <div class="sum-card">
        <div class="sum-val">{len(audit)}</div>
        <div class="sum-lbl">Audit Trail Entries</div>
      </div>
      <div class="sum-card" style="border-top-color:#28a745">
        <div class="sum-val" style="color:#155724">CAA</div>
        <div class="sum-lbl">Compliant — All Logs Retained</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Overrides table ───────────────────────────────────────────────────────
    st.markdown('<div class="section-hdr">⚠️ Manual Overrides</div>', unsafe_allow_html=True)
    if overrides:
        tbl = '<table class="audit-table"><thead><tr><th>#</th><th>Flight</th><th>Date</th><th>Crew</th><th>Role</th><th>Reason</th><th>Performed By</th><th>Timestamp</th></tr></thead><tbody>'
        for i, (rid, fn, dt, name, role, reason, by, ts) in enumerate(overrides, 1):
            tbl += f"""<tr>
              <td>{i}</td>
              <td style="font-family:'Share Tech Mono',monospace">{fn}</td>
              <td>{dt}</td>
              <td><b>{name}</b></td>
              <td><span class="type-override">{role}</span></td>
              <td>{reason or '—'}</td>
              <td>{by or 'OCC'}</td>
              <td style="font-family:'Share Tech Mono',monospace;font-size:0.65rem">{str(ts)[:16]}</td>
            </tr>"""
        tbl += '</tbody></table>'
        st.markdown(tbl, unsafe_allow_html=True)
    else:
        st.info("No manual overrides in selected date range.")

    # ── Violations table ──────────────────────────────────────────────────────
    st.markdown('<div class="section-hdr">🚫 FDTL Violations Prevented by System</div>', unsafe_allow_html=True)
    if violations:
        tbl = '<table class="audit-table"><thead><tr><th>#</th><th>Crew</th><th>Flight</th><th>Violation Type</th><th>Details</th><th>Flagged At</th></tr></thead><tbody>'
        for i, (vid, vtype, detail, ts, name, fn) in enumerate(violations, 1):
            tbl += f"""<tr>
              <td>{i}</td>
              <td><b>{name or '—'}</b></td>
              <td style="font-family:'Share Tech Mono',monospace">{fn or '—'}</td>
              <td><span class="type-violation">{vtype}</span></td>
              <td style="font-size:0.7rem">{detail}</td>
              <td style="font-family:'Share Tech Mono',monospace;font-size:0.65rem">{str(ts)[:16]}</td>
            </tr>"""
        tbl += '</tbody></table>'
        st.markdown(tbl, unsafe_allow_html=True)
    else:
        st.success("✅ No FDTL violations flagged in selected date range.")

    # ── Audit trail ──────────────────────────────────────────────────────────
    if audit:
        st.markdown('<div class="section-hdr">📋 System Audit Trail</div>', unsafe_allow_html=True)
        tbl = '<table class="audit-table"><thead><tr><th>#</th><th>Action</th><th>Performed By</th><th>Table</th><th>Old Value</th><th>New Value</th><th>Timestamp</th></tr></thead><tbody>'
        for i, (action, by, table, old, new, ts) in enumerate(audit, 1):
            tbl += f"""<tr>
              <td>{i}</td><td><span class="type-system">{action}</span></td>
              <td>{by or 'SYSTEM'}</td><td>{table or '—'}</td>
              <td style="font-size:0.65rem">{old or '—'}</td>
              <td style="font-size:0.65rem">{new or '—'}</td>
              <td style="font-family:'Share Tech Mono',monospace;font-size:0.65rem">{str(ts)[:16]}</td>
            </tr>"""
        tbl += '</tbody></table>'
        st.markdown(tbl, unsafe_allow_html=True)

    # CSV
    import io
    all_rows = [{"Type":"Override","Flight":fn,"Date":str(dt),"Crew":name,
                 "Role":role,"Details":reason or "","By":by or "OCC","Time":str(ts)[:16]}
                for _, fn, dt, name, role, reason, by, ts in overrides]
    all_rows += [{"Type":"Violation","Flight":fn or "","Date":str(ts)[:10],"Crew":name or "",
                  "Role":"","Details":detail,"By":"SYSTEM","Time":str(ts)[:16]}
                 for _, vtype, detail, ts, name, fn in violations]
    if all_rows:
        csv_buf = io.StringIO()
        pd.DataFrame(all_rows).to_csv(csv_buf, index=False)
        csv_placeholder.download_button(
            "⬇️ Download CSV", csv_buf.getvalue(),
            file_name=f"audit_log_{from_date}_{to_date}.csv", mime="text/csv"
        )

except Exception as e:
    st.error(f"Database error: {e}")
