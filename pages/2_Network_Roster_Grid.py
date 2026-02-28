import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Network Roster Grid", page_icon="📊", layout="wide")

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

# ── CSS + Hover Dropdown ───────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Exo+2:wght@300;400;600&family=Share+Tech+Mono&display=swap');

  .page-title {
    font-family: 'Orbitron', monospace;
    font-size: 1.3rem; font-weight: 700;
    color: #1a1a2e; letter-spacing: 0.1em;
    text-transform: uppercase; margin-bottom: 0.2rem;
  }
  .page-sub {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.7rem; color: #888; letter-spacing: 0.15em; margin-bottom: 1rem;
  }

  /* ── Grid wrapper ── */
  .grid-wrapper {
    overflow-x: auto;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    background: #fff;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }
  .roster-grid {
    border-collapse: collapse;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.58rem;
    width: 100%;
  }

  /* ── Header row ── */
  .roster-grid th {
    background: #1a1a2e;
    color: #fff;
    padding: 7px 4px;
    text-align: center;
    border: 1px solid #2d2d4e;
    font-size: 0.55rem;
    white-space: nowrap;
    letter-spacing: 0.05em;
  }
  .roster-grid th.flight-col {
    background: #0f0f1a;
    color: #a0aec0;
    text-align: left;
    padding-left: 10px;
    min-width: 90px;
    font-size: 0.6rem;
  }

  /* ── Data cells ── */
  .roster-grid td {
    padding: 3px 3px;
    border: 1px solid #e8ecf0;
    text-align: center;
    vertical-align: top;
    min-width: 66px;
    background: #fff;
    position: relative;
  }
  .roster-grid td.flight-id {
    background: #f7f8fc;
    color: #1a1a2e;
    font-weight: bold;
    text-align: left;
    padding-left: 10px;
    border-right: 2px solid #c8cfe0;
    white-space: nowrap;
    font-size: 0.62rem;
    font-family: 'Exo 2', sans-serif;
  }
  .roster-grid tr:hover td { background: #f0f4ff; }
  .roster-grid tr:hover td.flight-id { background: #e4eaf8; }

  /* ── Cell content ── */
  .crew-cell {
    display: flex;
    flex-direction: column;
    gap: 1px;
    cursor: pointer;
  }
  .crew-name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 80px;
    display: block;
    font-size: 0.58rem;
  }
  .lcc  { color: #b35900; font-weight: 700; }
  .cc   { color: #155724; font-weight: 600; }
  .exp  { color: #cc0000 !important; text-decoration: underline dotted; }
  .ovr  { color: #8b0000 !important; }
  .empty-cell { color: #ccc; font-size: 0.55rem; }

  /* ── Hover popup ── */
  .cell-wrapper {
    position: relative;
    display: inline-block;
    width: 100%;
  }
  .hover-popup {
    display: none;
    position: absolute;
    top: 0;
    left: 105%;
    z-index: 9999;
    min-width: 200px;
    background: #fff;
    border: 1px solid #1a1a2e;
    border-radius: 8px;
    padding: 0.7rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    font-family: 'Exo 2', sans-serif;
    font-size: 0.75rem;
    text-align: left;
    pointer-events: none;
  }
  .hover-popup .pop-flight {
    font-family: 'Orbitron', monospace;
    font-size: 0.65rem;
    font-weight: 700;
    color: #1a1a2e;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.3rem;
    margin-bottom: 0.4rem;
  }
  .hover-popup .pop-crew { padding: 2px 0; color: #333; }
  .hover-popup .pop-lcc  { color: #b35900; font-weight: 700; }
  .hover-popup .pop-cc   { color: #155724; }
  .hover-popup .pop-ovr  { color: #cc0000; font-size: 0.65rem; }
  .hover-popup .pop-exp  { color: #cc0000; font-size: 0.62rem; font-style: italic; }
  .cell-wrapper:hover .hover-popup { display: block; }

  /* ── Legend ── */
  .legend {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem; color: #888; margin-top: 0.6rem;
  }

  /* ── Print button ── */
  .print-btn {
    display: inline-block;
    background: #1a1a2e; color: #fff;
    border: none; border-radius: 5px;
    padding: 6px 16px; font-size: 0.75rem;
    cursor: pointer; font-family: 'Share Tech Mono', monospace;
    letter-spacing: 0.08em; margin-bottom: 1rem;
  }
  .print-btn:hover { background: #2d2d4e; }

  @media print {
    .stSidebar, .stButton, button, .print-btn { display: none !important; }
    .grid-wrapper { box-shadow: none; border: 1px solid #ccc; }
  }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">📊 Network Roster Grid</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">MASTER CONTROL VIEW — 30-DAY ROLLING SCHEDULE — ALL FLIGHTS × ALL CREW</div>', unsafe_allow_html=True)

# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.markdown("**📅 Date Range**")
start_date = st.sidebar.date_input("From", value=date.today())
end_date   = st.sidebar.date_input("To",   value=date.today() + timedelta(days=29))
st.sidebar.markdown("---")
st.sidebar.markdown("**🔍 Filter**")
show_alerts_only = st.sidebar.checkbox("Highlight expiring quals only", value=False)

# Print button
st.markdown("""
<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
""", unsafe_allow_html=True)

# CSV download placeholder — filled after data loads
csv_placeholder = st.empty()

try:
    conn = get_connection()
    cur  = conn.cursor()
    today = date.today()

    # Get expiring crew IDs and details
    try:
        cur.execute("""
            SELECT crew_id, qualification_type, expiry_date
            FROM crew_qualifications WHERE expiry_date <= %s ORDER BY expiry_date
        """, (today + timedelta(days=3),))
        expiring_crew_ids = set()
        crew_qual_details = {}
        for crew_id, qt, exp in cur.fetchall():
            expiring_crew_ids.add(crew_id)
            crew_qual_details.setdefault(crew_id, []).append(f"{qt} {exp.strftime('%d %b')}")
    except Exception:
        expiring_crew_ids = set()
        crew_qual_details = {}

    # Fetch full roster
    num_days = max(1, (end_date - start_date).days + 1)
    days = [start_date + timedelta(days=i) for i in range(num_days)]

    cur.execute("""
        SELECT
            fs.flight_number,
            fs.origin || '→' || fs.destination AS route,
            TO_CHAR(fs.departure_time, 'HH24:MI') AS dep,
            fs.departure_time::date AS duty_date,
            cm.full_name,
            cm.role,
            cm.id AS crew_id,
            r.is_manual_override
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        JOIN crew_master     cm ON cm.id = r.crew_id
        WHERE fs.departure_time::date BETWEEN %s AND %s
        ORDER BY fs.flight_number, fs.departure_time::date, cm.role DESC, cm.full_name
    """, (start_date, end_date))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Build data structure: {flight: {date: [(name, role, crew_id, override)]}}
    from collections import defaultdict, OrderedDict
    data     = defaultdict(lambda: defaultdict(list))
    flight_routes = OrderedDict()  # flight -> "XYZ301 KHI→ISB 0800"

    for flight, route, dep, duty_date, name, role, crew_id, override in rows:
        data[flight][duty_date].append((name, role, crew_id, override))
        if flight not in flight_routes:
            flight_routes[flight] = f"{flight}  {route}  {dep}"

    flights_list = sorted(flight_routes.keys())

    def abbrev(name):
        parts = name.replace("Capt. ", "").strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}.{parts[-1]}"
        return name[:7]

    # ── Build HTML table ──────────────────────────────────────────────────────
    # Header
    header = '<th class="flight-col">FLIGHT</th>'
    for d in days:
        header += f'<th>{d.strftime("%d")}<br>{d.strftime("%a").upper()}</th>'

    rows_html = ""
    csv_rows  = []

    for flight in flights_list:
        label = flight_routes[flight]
        row   = f'<td class="flight-id">{label}</td>'
        csv_row = [flight]

        for d in days:
            crew_list = data[flight].get(d, [])
            csv_cell  = []

            if not crew_list:
                row += '<td><span class="empty-cell">—</span></td>'
                csv_row.append("")
                continue

            # Build popup content
            popup = f'<div class="pop-flight">{label} · {d.strftime("%d %b")}</div>'
            cell_html = '<div class="crew-cell">'

            for name, role, crew_id, override in crew_list:
                short = abbrev(name)
                css   = "lcc" if role == "LCC" else "cc"
                extra = ""
                pop_extra = ""

                if override:
                    css   += " ovr"
                    extra  = " ⚠"
                    pop_extra += '<div class="pop-ovr">⚠️ Manual Override</div>'

                if crew_id in expiring_crew_ids:
                    css   += " exp"
                    quals  = " | ".join(crew_qual_details.get(crew_id, []))
                    extra += " 🔴"
                    pop_extra += f'<div class="pop-exp">🔴 {quals}</div>'

                cell_html += f'<span class="crew-name {css}">{short}{extra}</span>'
                popup     += f'<div class="pop-crew"><span class="pop-{"lcc" if role=="LCC" else "cc"}">[{role}] {name}</span>{pop_extra}</div>'
                csv_cell.append(f"{role}:{name}")

            cell_html += '</div>'
            full_cell  = f'<div class="cell-wrapper">{cell_html}<div class="hover-popup">{popup}</div></div>'
            row       += f'<td>{full_cell}</td>'
            csv_row.append(" | ".join(csv_cell))

        rows_html += f'<tr>{row}</tr>'
        csv_rows.append(csv_row)

    table_html = f"""
    <div class="grid-wrapper">
      <table class="roster-grid">
        <thead><tr>{header}</tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    <div class="legend">
      <span style="color:#b35900;font-weight:700">■</span> LCC &nbsp;
      <span style="color:#155724">■</span> CC &nbsp;
      <span style="color:#8b0000">■</span> Manual Override &nbsp;
      <span style="color:#cc0000;text-decoration:underline dotted">■</span> Qualification Expiring &nbsp;
      · Hover cell for full crew details
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

    # ── CSV Download ──────────────────────────────────────────────────────────
    import io
    day_headers = [d.strftime("%d-%b") for d in days]
    csv_df = pd.DataFrame(csv_rows, columns=["Flight"] + day_headers)
    csv_buf = io.StringIO()
    csv_df.to_csv(csv_buf, index=False)
    csv_placeholder.download_button(
        label="⬇️ Download CSV",
        data=csv_buf.getvalue(),
        file_name=f"network_roster_{start_date}_{end_date}.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"Database error: {e}")
