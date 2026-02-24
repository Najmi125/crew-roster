import streamlit as st
from dotenv import load_dotenv
import psycopg2
import pandas as pd
from datetime import date, timedelta
import os

load_dotenv()

st.set_page_config(
    page_title="Crew Scheduling System",
    page_icon="✈️",
    layout="wide"
)

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://raw.githubusercontent.com/Najmi125/crew-roster/main/assets/cc.jpg", width=150)
st.sidebar.title("✈️ Crew Roster")
st.sidebar.markdown("---")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@400;600;700&display=swap');
  .occ-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.1rem; font-weight: 700;
    letter-spacing: 0.08em; color: #000;
    text-transform: uppercase; line-height: 1; margin-bottom: 2px;
  }
  .occ-sub {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.7rem; color: #888; letter-spacing: 0.2em; margin-bottom: 0.8rem;
  }
  .live-badge {
    display: inline-block; background: #efffef; color: #006600;
    border: 1px solid #006600; border-radius: 3px; padding: 2px 10px;
    font-family: 'Share Tech Mono', monospace; font-size: 0.7rem; margin-bottom: 1rem;
  }
  .qual-alert {
    background: #fff8e1; border-left: 4px solid #f9a825;
    padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 0.4rem; font-size: 0.85rem;
  }
  .qual-expired {
    background: #ffebee; border-left: 4px solid #c62828;
    padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 0.4rem; font-size: 0.85rem;
  }
  .grid-wrapper {
    overflow-x: auto; border: 1px solid #dee2e6; border-radius: 6px; background: #fff;
  }
  .roster-grid {
    border-collapse: collapse; font-family: 'Share Tech Mono', monospace;
    font-size: 0.6rem; width: 100%; min-width: 1200px;
  }
  .roster-grid th {
    background: #1a1a2e; color: #fff; padding: 6px 4px; text-align: center;
    border: 1px solid #2d2d4e; font-size: 0.55rem; white-space: nowrap;
  }
  .roster-grid th.flight-col {
    background: #0f0f1a; color: #aaaacc; text-align: left; padding-left: 8px; min-width: 80px;
  }
  .roster-grid td {
    padding: 3px 4px; border: 1px solid #eee; text-align: center;
    vertical-align: top; min-width: 68px; background: #fff;
  }
  .roster-grid td.flight-id {
    background: #f0f0f5; color: #1a1a2e; font-weight: bold;
    text-align: left; padding-left: 8px; border-right: 2px solid #ccccdd;
    white-space: nowrap; font-size: 0.62rem;
  }
  .roster-grid tr:hover td { background: #f0f4ff; }
  .roster-grid tr:hover td.flight-id { background: #e0e4f5; }
  .crew-cell { display: flex; flex-direction: column; gap: 1px; }
  .crew-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 82px; display: block; }
  .lcc { color: #b35900; font-weight: bold; }
  .cc  { color: #006633; font-weight: bold; }
  .expiring { color: #e65100 !important; text-decoration: underline dotted; }
  .override-name { color: #cc0000 !important; }
  .empty-cell { color: #ccc; }
  .legend { font-family: 'Share Tech Mono', monospace; font-size: 0.65rem; color: #888; margin-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="occ-title">AI Generated Crew Scheduling System</div>', unsafe_allow_html=True)
st.markdown('<div class="occ-sub">OPERATIONAL CONTROL CENTRE — DECISION SUPPORT PLATFORM</div>', unsafe_allow_html=True)
st.markdown('<span class="live-badge">● LIVE — Operational Roster</span>', unsafe_allow_html=True)

try:
    conn = get_connection()
    cur  = conn.cursor()
    today    = date.today()
    tomorrow = today + timedelta(days=1)

    # ── Qualification Alerts ──────────────────────────────────────────────────
    try:
        cur.execute("""
            SELECT cm.full_name, cm.employee_id, cq.qualification_type, cq.expiry_date
            FROM crew_qualifications cq
            JOIN crew_master cm ON cm.id = cq.crew_id
            WHERE cq.expiry_date <= %s
            ORDER BY cq.expiry_date, cm.full_name
        """, (today + timedelta(days=3),))
        alerts = cur.fetchall()

        cur.execute("""
            SELECT DISTINCT crew_id FROM crew_qualifications WHERE expiry_date <= %s
        """, (today + timedelta(days=3),))
        expiring_crew_ids = {row[0] for row in cur.fetchall()}

        if alerts:
            with st.expander(f"⚠️  {len(alerts)} Qualification Alert(s) — Click to expand", expanded=True):
                for name, emp_id, qual, exp in alerts:
                    days_left = (exp - today).days
                    if days_left < 0:
                        st.markdown(
                            f'<div class="qual-expired">🔴 <b>{name}</b> ({emp_id}) — '
                            f'<b>{qual}</b> EXPIRED on {exp} ({abs(days_left)} day(s) ago)</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div class="qual-alert">🟡 <b>{name}</b> ({emp_id}) — '
                            f'<b>{qual}</b> expires {exp} (in {days_left} day(s))</div>',
                            unsafe_allow_html=True
                        )
    except Exception:
        expiring_crew_ids = set()

    st.markdown("---")

    # ── Today & Tomorrow ──────────────────────────────────────────────────────
    cur.execute("""
        SELECT
            fs.departure_time::date AS duty_date,
            fs.flight_number,
            fs.origin || '→' || fs.destination AS route,
            TO_CHAR(fs.departure_time, 'HH24:MI') AS dep,
            TO_CHAR(fs.arrival_time,   'HH24:MI') AS arr,
            fs.aircraft_type,
            cm.full_name,
            cm.role,
            cm.employee_id,
            cm.id AS crew_id,
            r.is_manual_override
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        JOIN crew_master     cm ON cm.id = r.crew_id
        WHERE fs.departure_time::date IN (%s, %s)
        ORDER BY fs.departure_time, cm.role DESC, cm.full_name
    """, (today, tomorrow))
    rows = cur.fetchall()

    cols = ['duty_date','flight_number','route','dep','arr','aircraft_type',
            'full_name','role','employee_id','crew_id','is_manual_override']
    df = pd.DataFrame(rows, columns=cols)

    if df.empty:
        st.warning("No roster data found for today or tomorrow.")
    else:
        for duty_date in [today, tomorrow]:
            label  = "TODAY" if duty_date == today else "TOMORROW"
            day_df = df[df['duty_date'] == duty_date]
            if day_df.empty:
                continue

            st.subheader(f"📅 {label} — {duty_date.strftime('%A, %d %B %Y')}")

            for flight_num in sorted(day_df['flight_number'].unique()):
                fl_rows = day_df[day_df['flight_number'] == flight_num]
                fl_info = fl_rows.iloc[0]

                with st.expander(
                    f"✈️ {flight_num}  |  {fl_info['route']}  |  "
                    f"{fl_info['dep']}→{fl_info['arr']}  |  {fl_info['aircraft_type']}"
                ):
                    for _, crew_row in fl_rows.iterrows():
                        role_icon    = "🟡" if crew_row['role'] == 'LCC' else "🔵"
                        override_tag = " ⚠️ *Manual Override*" if crew_row['is_manual_override'] else ""
                        qual_warn    = " 🔴 *Qual expiring!*" if crew_row['crew_id'] in expiring_crew_ids else ""
                        st.markdown(
                            f"{role_icon} **{crew_row['role']}** — "
                            f"{crew_row['full_name']} ({crew_row['employee_id']})"
                            f"{override_tag}{qual_warn}"
                        )
            st.markdown("---")

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Database connection error: {e}")
