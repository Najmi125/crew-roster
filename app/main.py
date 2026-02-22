import streamlit as st
from dotenv import load_dotenv
import psycopg2
import pandas as pd
from datetime import date, timedelta
import os

load_dotenv()

st.set_page_config(
    page_title="Crew Roster System",
    page_icon="✈️",
    layout="wide"
)

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

# Sidebar
st.sidebar.image("https://raw.githubusercontent.com/Najmi125/crew-roster/main/assets/cc.jpg", width=150)
st.sidebar.title("✈️ Crew Roster")
st.sidebar.markdown("---")
st.sidebar.markdown("**📅 Date Range**")
start_date = st.sidebar.date_input("From", value=date.today())
end_date = st.sidebar.date_input("To", value=date.today() + timedelta(days=29))
st.sidebar.markdown("---")

# Custom CSS
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@400;600;700&display=swap');

  .occ-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.8rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #000000;
    text-transform: uppercase;
    margin-bottom: 0;
    line-height: 1;
  }
  .occ-sub {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.75rem;
    color: #888888;
    letter-spacing: 0.2em;
    margin-bottom: 1rem;
  }
  .metric-bar {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  .metric-card {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-top: 3px solid #1a1a2e;
    border-radius: 4px;
    padding: 0.6rem 1.2rem;
    flex: 1;
    font-family: 'Barlow Condensed', sans-serif;
  }
  .metric-label {
    font-size: 0.65rem;
    color: #888888;
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }
  .metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a1a2e;
    line-height: 1.1;
  }
  .metric-card.violation .metric-value { color: #cc0000; }
  .grid-wrapper {
    overflow-x: auto;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    background: #ffffff;
  }
  .roster-grid {
    border-collapse: collapse;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.6rem;
    width: 100%;
    min-width: 1200px;
  }
  .roster-grid th {
    background: #1a1a2e;
    color: #ffffff;
    padding: 6px 4px;
    text-align: center;
    border: 1px solid #2d2d4e;
    font-size: 0.58rem;
    letter-spacing: 0.05em;
    white-space: nowrap;
  }
  .roster-grid th.flight-col {
    background: #0f0f1a;
    color: #aaaacc;
    text-align: left;
    padding-left: 8px;
    min-width: 80px;
  }
  .roster-grid td {
    padding: 3px 4px;
    border: 1px solid #eeeeee;
    text-align: center;
    color: #333333;
    vertical-align: top;
    min-width: 72px;
    max-width: 90px;
    background: #ffffff;
  }
  .roster-grid td.flight-id {
    background: #f0f0f5;
    color: #1a1a2e;
    font-weight: bold;
    text-align: left;
    padding-left: 8px;
    border-right: 2px solid #ccccdd;
    white-space: nowrap;
    font-size: 0.65rem;
  }
  .roster-grid tr:hover td { background: #f0f4ff; }
  .roster-grid tr:hover td.flight-id { background: #e0e4f5; }
  .crew-cell {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .crew-name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 85px;
    display: block;
  }
  .lcc { color: #b35900; font-weight: bold; }
  .cc  { color: #006633; font-weight: bold; }
  .empty-cell { color: #cccccc; }
  .override { color: #cc0000 !important; }
  .live-badge {
    display: inline-block;
    background: #efffef;
    color: #006600;
    border: 1px solid #006600;
    border-radius: 3px;
    padding: 2px 8px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.7rem;
    margin-bottom: 1rem;
  }
  .sim-badge { display: none; }
  .legend {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    color: #888888;
    margin-top: 0.5rem;
  }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="occ-title">AI Generated Crew Scheduling System</div>', unsafe_allow_html=True)
st.markdown('<div class="occ-sub">30 days rolling roster</div>', unsafe_allow_html=True)

st.markdown('<span class="live-badge">● LIVE — Operational Roster</span>', unsafe_allow_html=True)

try:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM crew_master WHERE is_active = TRUE")
    active_crew = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM flight_schedule")
    total_flights = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM roster")
    total_assignments = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM legality_violations")
    violations = cur.fetchone()[0]

    viol_class = "violation" if violations > 0 else ""
    st.markdown(f"""
    <div class="metric-bar">
      <div class="metric-card"><div class="metric-label">👨‍✈️ Active Crew</div><div class="metric-value">{active_crew}</div></div>
      <div class="metric-card"><div class="metric-label">✈️ Flights Scheduled</div><div class="metric-value">{total_flights}</div></div>
      <div class="metric-card"><div class="metric-label">📋 Assignments</div><div class="metric-value">{total_assignments}</div></div>
      <div class="metric-card {viol_class}"><div class="metric-label">⚠️ Violations</div><div class="metric-value">{violations}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Date range from sidebar
    num_days = (end_date - start_date).days + 1
    days = [start_date + timedelta(days=i) for i in range(num_days)]

    cur.execute("""
        SELECT
            fs.flight_number,
            fs.departure_time::date AS duty_date,
            cm.full_name,
            cm.role,
            r.is_manual_override
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        JOIN crew_master cm ON cm.id = r.crew_id
        WHERE fs.departure_time::date BETWEEN %s AND %s
        ORDER BY fs.flight_number, fs.departure_time::date, cm.role DESC, cm.full_name
    """, (start_date, end_date))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    from collections import defaultdict
    data = defaultdict(lambda: defaultdict(list))
    flights_set = []
    for flight, duty_date, name, role, override in rows:
        data[flight][duty_date].append((name, role, override))
        if flight not in flights_set:
            flights_set.append(flight)
    flights_set = sorted(set(flights_set))

    def abbrev(name):
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}.{parts[-1]}"
        return name[:7]

    header = '<th class="flight-col">FLIGHT</th>'
    for d in days:
        header += f'<th>{d.strftime("%d")}<br>{d.strftime("%a").upper()}</th>'

    rows_html = ""
    for flight in flights_set:
        row = f'<td class="flight-id">{flight}</td>'
        for d in days:
            crew_list = data[flight].get(d, [])
            if not crew_list:
                row += '<td><span class="empty-cell">—</span></td>'
            else:
                cell = '<div class="crew-cell">'
                for name, role, override in crew_list:
                    css = "lcc" if role == "LCC" else "cc"
                    if override:
                        css += " override"
                    short = abbrev(name)
                    cell += f'<span class="crew-name {css}" title="{name} ({role})">{short}</span>'
                cell += '</div>'
                row += f'<td>{cell}</td>'
        rows_html += f'<tr>{row}</tr>'

    table_html = f"""
    <div class="grid-wrapper">
      <table class="roster-grid">
        <thead><tr>{header}</tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    <div class="legend">
      <span style="color:#b35900">■</span> LCC &nbsp;&nbsp;
      <span style="color:#006633">■</span> CC &nbsp;&nbsp;
      <span style="color:#cc0000">■</span> Manual Override
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Database connection error: {e}")
