import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Crew Utilization Analytics", page_icon="📈", layout="wide")

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
  .util-table { width:100%; border-collapse:collapse; font-family:'Exo 2',sans-serif; font-size:0.78rem; }
  .util-table th { background:#1a1a2e; color:#fff; padding:8px 10px; text-align:left; font-size:0.68rem; letter-spacing:0.08em; text-transform:uppercase; }
  .util-table td { padding:7px 10px; border-bottom:1px solid #eee; }
  .util-table tr:hover td { background:#f0f4ff; }
  .zone-over  { background:#fff0f0 !important; color:#721c24; font-weight:700; }
  .zone-under { background:#fff8e1 !important; color:#856404; }
  .zone-ok    { background:#f0fff4 !important; color:#155724; }
  .bar-bg { background:#e9ecef; border-radius:3px; height:10px; }
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

    cur.execute(f"""
        SELECT
            cm.id, cm.full_name, cm.role, cm.employee_id,
            COUNT(r.id)                                          AS total_sectors,
            COALESCE(SUM(dl.total_duty_hours), 0)               AS total_hours,
            COUNT(CASE WHEN EXTRACT(HOUR FROM fs.departure_time) < 6 THEN 1 END) AS early_deps,
            COUNT(CASE WHEN EXTRACT(HOUR FROM fs.departure_time) >= 20 THEN 1 END) AS night_deps,
            COUNT(CASE WHEN r.is_manual_override THEN 1 END)    AS overrides
        FROM crew_master cm
        LEFT JOIN roster r ON r.crew_id = cm.id
        LEFT JOIN flight_schedule fs ON fs.id = r.flight_id
            AND fs.departure_time::date BETWEEN %s AND %s
        LEFT JOIN duty_log dl ON dl.crew_id = cm.id
            AND dl.duty_start >= %s AND dl.duty_start <= %s
        WHERE cm.is_active = TRUE {role_sql}
        GROUP BY cm.id, cm.full_name, cm.role, cm.employee_id
        ORDER BY total_hours DESC
    """, (since_28, today, since_28, today))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    df = pd.DataFrame(rows, columns=['id','full_name','role','employee_id',
                                      'sectors','hours','early','night','overrides'])
    df['hours'] = df['hours'].astype(float)

    if df.empty:
        st.warning("No utilization data found.")
    else:
        avg_hrs = df['hours'].mean()
        max_hrs = df['hours'].max()
        over    = len(df[df['hours'] > avg_hrs * 1.2])
        under   = len(df[df['hours'] < avg_hrs * 0.8])

        # Summary cards
        st.markdown(f"""
        <div class="summary-cards">
          <div class="sum-card"><div class="sum-val">{avg_hrs:.1f}h</div><div class="sum-lbl">Avg Hours / Crew</div></div>
          <div class="sum-card"><div class="sum-val">{max_hrs:.1f}h</div><div class="sum-lbl">Max Hours (any crew)</div></div>
          <div class="sum-card" style="border-top-color:#dc3545"><div class="sum-val" style="color:#dc3545">{over}</div><div class="sum-lbl">Over-Utilized Crew</div></div>
          <div class="sum-card" style="border-top-color:#f59e0b"><div class="sum-val" style="color:#856404">{under}</div><div class="sum-lbl">Under-Utilized Crew</div></div>
        </div>
        """, unsafe_allow_html=True)

        # Table
        table_html = """
        <table class="util-table">
          <thead><tr>
            <th>#</th><th>Name</th><th>Role</th><th>ID</th>
            <th>Sectors</th><th>Duty Hours</th><th>Utilization</th>
            <th>Early Dep</th><th>Night Dep</th><th>Overrides</th><th>Zone</th>
          </tr></thead><tbody>
        """
        for i, row in df.iterrows():
            pct = (row['hours'] / 100 * 100) if max_hrs > 0 else 0
            bar_color = "#dc3545" if row['hours'] > avg_hrs * 1.2 else ("#f59e0b" if row['hours'] < avg_hrs * 0.8 else "#28a745")

            if row['hours'] > avg_hrs * 1.2:
                zone_class, zone_label = "zone-over",  "🔴 Over"
            elif row['hours'] < avg_hrs * 0.8:
                zone_class, zone_label = "zone-under", "🟡 Under"
            else:
                zone_class, zone_label = "zone-ok",    "✅ Balanced"

            bar = f'<div class="bar-bg"><div class="bar-fill" style="width:{min(pct,100):.0f}%;background:{bar_color}"></div></div>'

            table_html += f"""
            <tr>
              <td>{i+1}</td>
              <td><b>{row['full_name']}</b></td>
              <td>{'🟡 LCC' if row['role']=='LCC' else '🔵 CC'}</td>
              <td style="font-family:'Share Tech Mono',monospace;font-size:0.7rem">{row['employee_id']}</td>
              <td style="text-align:center">{int(row['sectors'])}</td>
              <td><b>{row['hours']:.1f}h</b> {bar}</td>
              <td style="text-align:center">{row['hours']/100*100:.0f}%</td>
              <td style="text-align:center">{int(row['early'])}</td>
              <td style="text-align:center">{int(row['night'])}</td>
              <td style="text-align:center">{'⚠️ '+str(int(row['overrides'])) if row['overrides'] > 0 else '—'}</td>
              <td class="{zone_class}">{zone_label}</td>
            </tr>"""

        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)

        # CSV
        import io
        csv_buf = io.StringIO()
        df.drop(columns=['id']).to_csv(csv_buf, index=False)
        csv_placeholder.download_button(
            "⬇️ Download CSV", csv_buf.getvalue(),
            file_name=f"utilization_{today}.csv", mime="text/csv"
        )

except Exception as e:
    st.error(f"Database error: {e}")
