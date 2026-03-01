import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
from collections import defaultdict, OrderedDict
import io
import os

load_dotenv()

st.set_page_config(page_title="Network Roster Grid", page_icon="📊", layout="wide")

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
  .page-sub   { font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#888; letter-spacing:0.15em; margin-bottom:0.6rem; }
  .grid-wrapper { overflow-x:auto; border:1px solid #dee2e6; border-radius:8px; background:#fff; box-shadow:0 2px 12px rgba(0,0,0,0.08); }
  .roster-grid  { border-collapse:collapse; font-family:'Share Tech Mono',monospace; font-size:0.58rem; width:100%; }
  .roster-grid th { background:#1a1a2e; color:#fff; padding:7px 4px; text-align:center; border:1px solid #2d2d4e; font-size:0.55rem; white-space:nowrap; letter-spacing:0.05em; }
  .roster-grid th.flight-col { background:#0f0f1a; color:#a0aec0; text-align:left; padding-left:10px; min-width:90px; font-size:0.6rem; }
  .roster-grid td { padding:3px 3px; border:1px solid #e8ecf0; text-align:center; vertical-align:top; min-width:66px; background:#fff; position:relative; }
  .roster-grid td.flight-id { background:#f7f8fc; color:#1a1a2e; font-weight:bold; text-align:left; padding-left:10px; border-right:2px solid #c8cfe0; white-space:nowrap; font-size:0.62rem; font-family:'Exo 2',sans-serif; }
  .roster-grid tr:hover td { background:#f0f4ff; }
  .roster-grid tr:hover td.flight-id { background:#e4eaf8; }
  .crew-cell { display:flex; flex-direction:column; gap:1px; cursor:pointer; }
  .crew-name { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:80px; display:block; font-size:0.58rem; }
  .lcc  { color:#b35900; font-weight:700; }
  .cc   { color:#155724; font-weight:600; }
  .warn { background:#fff8e1 !important; }
  .exp  { background:#fff0f0 !important; }
  .crew-warn { color:#856404 !important; text-decoration:underline dotted; }
  .crew-exp  { color:#cc0000 !important; text-decoration:underline dotted; font-weight:700; }
  .ovr  { color:#8b0000 !important; }
  .empty-cell { color:#ccc; font-size:0.55rem; }
  .cell-wrapper { position:relative; display:inline-block; width:100%; }
  .hover-popup { display:none; position:absolute; top:0; left:105%; z-index:9999; min-width:200px; background:#fff; border:1px solid #1a1a2e; border-radius:8px; padding:0.7rem; box-shadow:0 4px 20px rgba(0,0,0,0.2); font-family:'Exo 2',sans-serif; font-size:0.75rem; text-align:left; pointer-events:none; }
  .hover-popup .pop-flight { font-family:'Orbitron',monospace; font-size:0.65rem; font-weight:700; color:#1a1a2e; border-bottom:1px solid #eee; padding-bottom:0.3rem; margin-bottom:0.4rem; }
  .hover-popup .pop-crew { padding:2px 0; color:#333; }
  .hover-popup .pop-lcc  { color:#b35900; font-weight:700; }
  .hover-popup .pop-cc   { color:#155724; }
  .hover-popup .pop-ovr  { color:#cc0000; font-size:0.65rem; }
  .hover-popup .pop-warn { color:#856404; font-size:0.62rem; font-style:italic; }
  .hover-popup .pop-exp  { color:#cc0000; font-size:0.62rem; font-style:italic; }
  .cell-wrapper:hover .hover-popup { display:block; }
  .legend { font-family:'Share Tech Mono',monospace; font-size:0.65rem; color:#888; margin-top:0.6rem; }
  .print-btn { display:inline-block; background:#1a1a2e; color:#fff; border:none; border-radius:5px; padding:6px 16px; font-size:0.75rem; cursor:pointer; font-family:'Share Tech Mono',monospace; letter-spacing:0.08em; margin-bottom:1rem; }
  .print-btn:hover { background:#2d2d4e; }
  @media print { .stSidebar,.stButton,button,.print-btn { display:none !important; } .grid-wrapper { box-shadow:none; border:1px solid #ccc; } }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">📊 Network Roster Grid</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">MASTER CONTROL VIEW — 30-DAY ROLLING SCHEDULE — ALL FLIGHTS × ALL CREW</div>', unsafe_allow_html=True)

# ── Date Range (compact, inline, below title) ─────────────────────────────────
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    start_date = st.date_input("From", value=date.today(), label_visibility="collapsed",
                               help="Start date")
    st.caption("From")
with col2:
    max_to = start_date + timedelta(days=30)
    end_date = st.date_input("To", value=min(start_date + timedelta(days=29), max_to),
                             min_value=start_date, max_value=max_to,
                             label_visibility="collapsed", help="Max 30 days")
    st.caption(f"To (max {max_to.strftime('%d %b')})")

st.markdown('<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>', unsafe_allow_html=True)
csv_placeholder = st.empty()

try:
    conn = get_connection()
    cur  = conn.cursor()
    today = date.today()

    # Expiring (within 3 days) and expired crew
    try:
        cur.execute("""
            SELECT crew_id, qualification_type, expiry_date
            FROM crew_qualifications WHERE expiry_date <= %s ORDER BY expiry_date
        """, (today + timedelta(days=3),))
        expiring_crew_ids = set()   # within 3 days — yellow warning
        expired_crew_ids  = set()   # already expired — red
        crew_qual_details = {}
        for crew_id, qt, exp in cur.fetchall():
            days_left = (exp - today).days
            if days_left < 0:
                expired_crew_ids.add(crew_id)
            else:
                expiring_crew_ids.add(crew_id)
            crew_qual_details.setdefault(crew_id, []).append(
                (qt, exp, days_left)
            )
    except Exception:
        expiring_crew_ids = set()
        expired_crew_ids  = set()
        crew_qual_details = {}

    days = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    cur.execute("""
        SELECT fs.flight_number,
               fs.origin || '→' || fs.destination AS route,
               TO_CHAR(fs.departure_time, 'HH24:MI') AS dep,
               fs.departure_time::date AS duty_date,
               cm.full_name, cm.role, cm.id AS crew_id,
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

    data         = defaultdict(lambda: defaultdict(list))
    flight_routes = OrderedDict()

    for flight, route, dep, duty_date, name, role, crew_id, override in rows:
        data[flight][duty_date].append((name, role, crew_id, override))
        if flight not in flight_routes:
            flight_routes[flight] = f"{flight}  {route}  {dep}"

    flights_list = sorted(flight_routes.keys())

    def abbrev(name):
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}.{parts[-1]}"
        return name[:7]

    # ── Build HTML table ──────────────────────────────────────────────────────
    header = '<th class="flight-col">FLIGHT</th>'
    for d in days:
        header += f'<th>{d.strftime("%d")}<br>{d.strftime("%a").upper()}</th>'

    rows_html = ""
    csv_rows  = []

    for flight in flights_list:
        label   = flight_routes[flight]
        row     = f'<td class="flight-id">{label}</td>'
        csv_row = [flight]

        for d in days:
            crew_list = data[flight].get(d, [])

            if not crew_list:
                row += '<td><span class="empty-cell">—</span></td>'
                csv_row.append("")
                continue

            # Determine cell background: red > yellow > white
            cell_has_expired  = any(cid in expired_crew_ids  for _, _, cid, _ in crew_list)
            cell_has_expiring = any(cid in expiring_crew_ids for _, _, cid, _ in crew_list)
            cell_class = "exp" if cell_has_expired else ("warn" if cell_has_expiring else "")

            popup     = f'<div class="pop-flight">{label} · {d.strftime("%d %b")}</div>'
            cell_html = '<div class="crew-cell">'
            csv_names = []
            csv_flags = []

            for name, role, crew_id, override in crew_list:
                short    = abbrev(name)
                name_css = "lcc" if role == "LCC" else "cc"
                extra    = ""
                pop_extra = ""

                if override:
                    name_css += " ovr"
                    extra     = " ⚠"
                    pop_extra += '<div class="pop-ovr">⚠️ Manual Override</div>'
                    csv_flags.append("OVERRIDE")

                if crew_id in expired_crew_ids:
                    name_css += " crew-exp"
                    quals = " | ".join(f"{qt} EXP {exp.strftime('%d %b')}"
                                       for qt, exp, _ in crew_qual_details.get(crew_id, []) if (exp - today).days < 0)
                    extra    += " 🔴"
                    pop_extra += f'<div class="pop-exp">🔴 EXPIRED: {quals}</div>'
                    csv_flags.append(f"QUAL EXPIRED:{quals}")
                elif crew_id in expiring_crew_ids:
                    name_css += " crew-warn"
                    quals = " | ".join(f"{qt} {exp.strftime('%d %b')} ({dl}d)"
                                       for qt, exp, dl in crew_qual_details.get(crew_id, []) if dl >= 0)
                    extra    += " 🟡"
                    pop_extra += f'<div class="pop-warn">🟡 Expiring: {quals}</div>'
                    csv_flags.append(f"QUAL EXPIRING:{quals}")

                cell_html += f'<span class="crew-name {name_css}">{short}{extra}</span>'
                popup     += f'<div class="pop-crew"><span class="pop-{"lcc" if role=="LCC" else "cc"}">[{role}] {name}</span>{pop_extra}</div>'
                csv_names.append(f"{role}:{name}")

            cell_html += '</div>'
            full_cell  = f'<div class="cell-wrapper">{cell_html}<div class="hover-popup">{popup}</div></div>'
            row       += f'<td class="{cell_class}">{full_cell}</td>'

            flags_str = " | ".join(csv_flags) if csv_flags else "LEGAL"
            csv_row.append(" | ".join(csv_names) + (f" [{flags_str}]" if csv_flags else ""))

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
      <span style="background:#fff8e1;padding:1px 4px;border:1px solid #ffc107">■</span> Qual expiring (≤3 days) &nbsp;
      <span style="background:#fff0f0;padding:1px 4px;border:1px solid #f5c6cb">■</span> Qual expired &nbsp;
      <span style="color:#8b0000">⚠</span> Manual Override &nbsp;
      · Hover cell for full crew details
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

    # ── CSV Download ──────────────────────────────────────────────────────────
    day_headers = [d.strftime("%d-%b") for d in days]
    csv_df  = pd.DataFrame(csv_rows, columns=["Flight"] + day_headers)
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
