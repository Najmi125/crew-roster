import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Daily Operations", page_icon="⚡", layout="wide")

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
  .flight-card {
    background:#fff; border:1px solid #e0e6f0; border-radius:8px;
    padding:0.9rem 1.2rem; margin-bottom:0.6rem;
    border-left:5px solid #1a1a2e;
    box-shadow:0 1px 6px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
  }
  .flight-card:hover { box-shadow:0 3px 14px rgba(0,0,0,0.12); }
  .flight-card.legal      { border-left-color:#28a745; }
  .flight-card.at-risk    { border-left-color:#f59e0b; }
  .flight-card.override   { border-left-color:#dc3545; }
  .card-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; }
  .card-flight { font-family:'Orbitron',monospace; font-size:0.9rem; font-weight:700; color:#1a1a2e; }
  .card-route  { font-family:'Exo 2',sans-serif; font-size:0.8rem; color:#555; }
  .card-time   { font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#1a1a2e; background:#f0f4ff; padding:3px 8px; border-radius:4px; }
  .status-badge { font-family:'Share Tech Mono',monospace; font-size:0.62rem; padding:2px 8px; border-radius:10px; font-weight:bold; letter-spacing:0.05em; }
  .status-legal   { background:#d4edda; color:#155724; }
  .status-risk    { background:#fff3cd; color:#856404; }
  .status-override{ background:#f8d7da; color:#721c24; }
  .crew-row { display:flex; flex-wrap:wrap; gap:0.4rem; margin-top:0.4rem; }
  .crew-tag { font-family:'Exo 2',sans-serif; font-size:0.72rem; padding:2px 8px; border-radius:12px; }
  .crew-lcc { background:#fff3e0; color:#b35900; border:1px solid #ffcc80; font-weight:700; }
  .crew-cc  { background:#e8f5e9; color:#155724; border:1px solid #a5d6a7; }
  .crew-exp { border-color:#ef9a9a !important; color:#b71c1c !important; }
  .day-header { font-family:'Orbitron',monospace; font-size:0.75rem; color:#1a1a2e; letter-spacing:0.15em; text-transform:uppercase; background:#f7f8fc; padding:0.4rem 0.8rem; border-radius:4px; margin:1rem 0 0.6rem; border-left:4px solid #f59e0b; }
  .print-btn { display:inline-block; background:#1a1a2e; color:#fff; border:none; border-radius:5px; padding:6px 16px; font-size:0.75rem; cursor:pointer; font-family:'Share Tech Mono',monospace; letter-spacing:0.08em; margin-bottom:1rem; }
  @media print { .stSidebar,.stButton,button,.print-btn { display:none !important; } }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">⚡ Daily Operations View</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">LIVE OCC TACTICAL SCREEN — TODAY + NEXT 48 HOURS — SORTED BY DEPARTURE</div>', unsafe_allow_html=True)
st.markdown('<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>', unsafe_allow_html=True)

csv_placeholder = st.empty()

try:
    conn = get_connection()
    cur  = conn.cursor()
    today    = date.today()
    end_view = today + timedelta(days=2)

    # Expiring crew
    try:
        cur.execute("SELECT crew_id, qualification_type, expiry_date FROM crew_qualifications WHERE expiry_date <= %s", (today + timedelta(days=3),))
        expiring_crew_ids = set()
        crew_qual_details = {}
        for crew_id, qt, exp in cur.fetchall():
            expiring_crew_ids.add(crew_id)
            crew_qual_details.setdefault(crew_id, []).append(f"{qt} {exp.strftime('%d %b')}")
    except:
        expiring_crew_ids = set()
        crew_qual_details = {}

    cur.execute("""
        SELECT
            fs.flight_number,
            fs.origin, fs.destination,
            fs.departure_time, fs.arrival_time,
            fs.aircraft_type,
            fs.departure_time::date AS duty_date,
            cm.full_name, cm.role, cm.employee_id, cm.id AS crew_id,
            r.is_manual_override
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        JOIN crew_master     cm ON cm.id = r.crew_id
        WHERE fs.departure_time::date BETWEEN %s AND %s
        ORDER BY fs.departure_time, cm.role DESC, cm.full_name
    """, (today, end_view))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    cols = ['flight_number','origin','destination','departure_time','arrival_time',
            'aircraft_type','duty_date','full_name','role','employee_id','crew_id','is_manual_override']
    df = pd.DataFrame(rows, columns=cols)

    if df.empty:
        st.warning("No flights found for next 48 hours.")
    else:
        csv_data = []
        for duty_date in sorted(df['duty_date'].unique()):
            day_label = "TODAY" if duty_date == today else ("TOMORROW" if duty_date == today + timedelta(days=1) else duty_date.strftime("%A %d %b").upper())
            st.markdown(f'<div class="day-header">📅 {day_label} — {duty_date.strftime("%A, %d %B %Y")}</div>', unsafe_allow_html=True)

            day_df = df[df['duty_date'] == duty_date]
            for flight_num in sorted(day_df['flight_number'].unique()):
                fl = day_df[day_df['flight_number'] == flight_num]
                info = fl.iloc[0]

                has_override = fl['is_manual_override'].any()
                has_exp      = fl['crew_id'].isin(expiring_crew_ids).any()

                if has_override:
                    card_class = "override"
                    status_class = "status-override"
                    status_label = "⚠️ MANUAL OVERRIDE"
                elif has_exp:
                    card_class = "at-risk"
                    status_class = "status-risk"
                    status_label = "🟡 AT RISK — QUAL EXPIRING"
                else:
                    card_class = "legal"
                    status_class = "status-legal"
                    status_label = "✅ LEGAL"

                dep_str = info['departure_time'].strftime('%H:%M')
                arr_str = info['arrival_time'].strftime('%H:%M')

                crew_tags = ""
                crew_csv  = []
                for _, cr in fl.iterrows():
                    tag_class = "crew-lcc" if cr['role'] == 'LCC' else "crew-cc"
                    if cr['crew_id'] in expiring_crew_ids:
                        tag_class += " crew-exp"
                        quals = " | ".join(crew_qual_details.get(cr['crew_id'], []))
                        label = f"{cr['full_name']} 🔴 {quals}"
                    else:
                        label = cr['full_name']
                    crew_tags += f'<span class="crew-tag {tag_class}">[{cr["role"]}] {label}</span>'
                    crew_csv.append(f"{cr['role']}:{cr['full_name']}")

                st.markdown(f"""
                <div class="flight-card {card_class}">
                  <div class="card-header">
                    <div>
                      <span class="card-flight">{flight_num}</span>
                      <span class="card-route"> &nbsp;{info['origin']} → {info['destination']} &nbsp;·&nbsp; {info['aircraft_type']}</span>
                    </div>
                    <div style="display:flex;gap:0.5rem;align-items:center;">
                      <span class="card-time">{dep_str} → {arr_str}</span>
                      <span class="status-badge {status_class}">{status_label}</span>
                    </div>
                  </div>
                  <div class="crew-row">{crew_tags}</div>
                </div>
                """, unsafe_allow_html=True)

                csv_data.append({
                    'Date': duty_date, 'Flight': flight_num,
                    'Route': f"{info['origin']}-{info['destination']}",
                    'Departure': dep_str, 'Arrival': arr_str,
                    'Status': status_label.replace("✅ ","").replace("🟡 ","").replace("⚠️ ",""),
                    'Crew': " | ".join(crew_csv)
                })

        # CSV download
        import io
        csv_df  = pd.DataFrame(csv_data)
        csv_buf = io.StringIO()
        csv_df.to_csv(csv_buf, index=False)
        csv_placeholder.download_button(
            label="⬇️ Download CSV",
            data=csv_buf.getvalue(),
            file_name=f"daily_ops_{today}.csv",
            mime="text/csv"
        )

except Exception as e:
    st.error(f"Database error: {e}")
