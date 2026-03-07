import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import io
import os

load_dotenv()

st.set_page_config(page_title="Crew Utilization Analytics", page_icon="📈", layout="wide")

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

st.sidebar.image(
    "https://raw.githubusercontent.com/Najmi125/crew-roster/main/assets/logo.png",
    use_container_width=True
)
st.sidebar.markdown("---")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Exo+2:wght@300;400;600&family=Share+Tech+Mono&display=swap');
  .page-title { font-family:'Orbitron',monospace; font-size:1.3rem; font-weight:700; color:#1a1a2e; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:0.2rem; }
  .page-sub   { font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#888; letter-spacing:0.15em; margin-bottom:1rem; }
  .util-table { width:100%; border-collapse:collapse; font-family:'Exo 2',sans-serif; font-size:0.78rem; }
  .util-table th { background:#1a1a2e; color:#fff; padding:8px 10px; text-align:left; font-size:0.68rem; letter-spacing:0.08em; text-transform:uppercase; }
  .util-table td { padding:7px 10px; border-bottom:1px solid #eee; }
  .util-table tr:hover td { background:#f0f4ff; }
  .zone-over  { background:#fff0f0 !important; color:#721c24; font-weight:700; }
  .zone-under { background:#fff8e1 !important; color:#856404; }
  .zone-ok    { background:#f0fff4 !important; color:#155724; }
  .bar-bg   { background:#e9ecef; border-radius:3px; height:10px; }
  .bar-fill { height:10px; border-radius:3px; }
  .summary-cards { display:grid; grid-template-columns:repeat(4,1fr); gap:0.8rem; margin-bottom:1.2rem; }
  .sum-card { background:#f7f8fc; border:1px solid #e0e6f0; border-radius:8px; padding:0.8rem 1rem; border-top:3px solid #1a1a2e; text-align:center; }
  .sum-val  { font-family:'Orbitron',monospace; font-size:1.1rem; font-weight:700; color:#1a1a2e; }
  .sum-lbl  { font-family:'Exo 2',sans-serif; font-size:0.65rem; color:#888; text-transform:uppercase; margin-top:2px; }
  .print-btn { display:inline-block; background:#1a1a2e; color:#fff; border:none; border-radius:5px; padding:6px 16px; font-size:0.75rem; cursor:pointer; font-family:'Share Tech Mono',monospace; letter-spacing:0.08em; margin-bottom:1rem; }
  @media print { .stSidebar,.stButton,button,.print-btn { display:none !important; } }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">📈 Crew Utilization Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">GOVERNANCE DASHBOARD — FAIRNESS & EFFICIENCY MONITORING — 28-DAY ROLLING WINDOW</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col2:
    role_filter = st.selectbox("Filter by Role", ["All", "LCC", "CC"])

st.markdown('<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>', unsafe_allow_html=True)
csv_placeholder = st.empty()

try:
    conn = get_connection()
    cur  = conn.cursor()
    today    = date.today()
    since_28 = today - timedelta(days=28)

    role_sql = "" if role_filter == "All" else f"AND cm.role = '{role_filter}'"

    # ── Get all active crew ───────────────────────────────────────────────────
    cur.execute(f"""
        SELECT id, full_name, role, employee_id
        FROM crew_master
        WHERE is_active = TRUE {role_sql}
        ORDER BY role, full_name
    """)
    crew_rows = cur.fetchall()

    # ── Get ALL roster sectors for current month (treat as completed) ──────────
    month_start = today.replace(day=1)
    month_end   = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    cur.execute("""
        SELECT r.crew_id, COUNT(r.id) AS sectors,
               COUNT(CASE WHEN EXTRACT(HOUR FROM fs.departure_time) < 6  THEN 1 END) AS early,
               COUNT(CASE WHEN EXTRACT(HOUR FROM fs.departure_time) >= 20 THEN 1 END) AS night,
               COUNT(CASE WHEN r.is_manual_override THEN 1 END) AS overrides
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        WHERE fs.departure_time::date BETWEEN %s AND %s
        GROUP BY r.crew_id
    """, (month_start, month_end))
    sector_map = {r[0]: r[1:] for r in cur.fetchall()}

    # ── Get duty hours from roster (all scheduled this month as planned) ───────
    cur.execute("""
        SELECT r.crew_id,
               COALESCE(SUM(EXTRACT(EPOCH FROM (fs.arrival_time - fs.departure_time))/3600), 0) AS hours
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        WHERE fs.departure_time::date BETWEEN %s AND %s
        GROUP BY r.crew_id
    """, (month_start, month_end))
    hours_map = {r[0]: float(r[1]) for r in cur.fetchall()}

    cur.close()
    conn.close()

    # ── Build dataframe ───────────────────────────────────────────────────────
    records = []
    for crew_id, full_name, role, emp_id in crew_rows:
        sectors, early, night, overrides = sector_map.get(crew_id, (0, 0, 0, 0))
        hours = hours_map.get(crew_id, 0.0)
        records.append({
            'id': crew_id, 'full_name': full_name, 'role': role,
            'employee_id': emp_id, 'sectors': int(sectors),
            'hours': hours, 'early': int(early),
            'night': int(night), 'overrides': int(overrides)
        })

    df = pd.DataFrame(records)

    if df.empty:
        st.warning("No utilization data found.")
    else:
        # Filter to crew with any activity for meaningful stats
        active_df = df[df['sectors'] > 0]
        avg_hrs = active_df['hours'].mean() if not active_df.empty else 0
        max_hrs = df['hours'].max()
        over    = len(active_df[active_df['hours'] > avg_hrs * 1.2]) if avg_hrs > 0 else 0
        under   = len(active_df[active_df['hours'] < avg_hrs * 0.8]) if avg_hrs > 0 else 0

        st.markdown(f"""
        <div class="summary-cards">
          <div class="sum-card"><div class="sum-val">{avg_hrs:.1f}h</div><div class="sum-lbl">Avg Hours / Active Crew</div></div>
          <div class="sum-card"><div class="sum-val">{max_hrs:.1f}h</div><div class="sum-lbl">Max Hours (any crew)</div></div>
          <div class="sum-card" style="border-top-color:#dc3545"><div class="sum-val" style="color:#dc3545">{over}</div><div class="sum-lbl">Over-Utilized</div></div>
          <div class="sum-card" style="border-top-color:#f59e0b"><div class="sum-val" style="color:#856404">{under}</div><div class="sum-lbl">Under-Utilized</div></div>
        </div>
        """, unsafe_allow_html=True)

        # Build display dataframe
        display_df = df.sort_values('hours', ascending=False).copy()
        display_df['Role']      = display_df['role'].apply(lambda x: '🟡 LCC' if x == 'LCC' else '🔵 CC')
        display_df['Hours']     = display_df['hours'].apply(lambda x: f'{x:.1f}h')
        display_df['Zone']      = display_df['hours'].apply(
            lambda h: '🔴 Over' if (avg_hrs > 0 and h > avg_hrs * 1.2)
                      else ('🟡 Under' if (avg_hrs > 0 and h < avg_hrs * 0.8) else '✅ Balanced')
        )
        display_df['Overrides'] = display_df['overrides'].apply(lambda x: f'⚠️ {x}' if x > 0 else '—')

        out = display_df.rename(columns={
            'full_name': 'Name', 'employee_id': 'ID',
            'sectors': 'Sectors', 'early': 'Early Dep',
            'night': 'Night Dep'
        })[['Name','Role','ID','Sectors','Hours','Zone','Early Dep','Night Dep','Overrides']]

        def color_zone(val):
            if '🔴' in str(val): return 'background-color:#fff0f0;color:#721c24;font-weight:bold'
            if '🟡' in str(val): return 'background-color:#fff8e1;color:#856404'
            if '✅' in str(val): return 'background-color:#f0fff4;color:#155724'
            return ''

        styled = out.style.applymap(color_zone, subset=['Zone'])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        csv_buf = io.StringIO()
        df.drop(columns=['id']).to_csv(csv_buf, index=False)
        csv_placeholder.download_button(
            "⬇️ Download CSV", csv_buf.getvalue(),
            file_name=f"utilization_{today}.csv", mime="text/csv"
        )

except Exception as e:
    st.error(f"Database error: {e}")
