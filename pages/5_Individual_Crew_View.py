import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Individual Crew View", page_icon="👤", layout="wide")

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
  .crew-profile { background:#f7f8fc; border:1px solid #e0e6f0; border-radius:8px; padding:1rem 1.5rem; margin-bottom:1rem; display:flex; gap:2rem; align-items:center; }
  .profile-name { font-family:'Orbitron',monospace; font-size:1rem; font-weight:700; color:#1a1a2e; }
  .profile-role-lcc { background:#fff3e0; color:#b35900; padding:2px 10px; border-radius:10px; font-family:'Share Tech Mono',monospace; font-size:0.7rem; font-weight:700; }
  .profile-role-cc  { background:#e8f5e9; color:#155724; padding:2px 10px; border-radius:10px; font-family:'Share Tech Mono',monospace; font-size:0.7rem; }
  .profile-stat { text-align:center; }
  .profile-stat-val { font-family:'Orbitron',monospace; font-size:1.1rem; font-weight:700; color:#1a1a2e; }
  .profile-stat-lbl { font-family:'Exo 2',sans-serif; font-size:0.65rem; color:#888; text-transform:uppercase; }
  .cal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:4px; margin-bottom:1rem; }
  .cal-header { font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:#888; text-align:center; padding:4px; }
  .cal-day { border-radius:5px; padding:5px 4px; min-height:52px; font-family:'Exo 2',sans-serif; font-size:0.65rem; border:1px solid #e8ecf0; }
  .cal-day.duty   { background:#fff3e0; border-color:#ffcc80; }
  .cal-day.rest   { background:#f7f8fc; }
  .cal-day.today  { border:2px solid #1a1a2e !important; }
  .cal-day.warn   { background:#fff8e1; border-color:#f59e0b; }
  .cal-date { font-weight:700; color:#1a1a2e; font-size:0.7rem; }
  .cal-flights { color:#b35900; font-size:0.6rem; margin-top:2px; }
  .cal-hours  { color:#555; font-size:0.58rem; }
  .fdtl-bar { background:#f7f8fc; border:1px solid #e0e6f0; border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1rem; }
  .fdtl-row { display:flex; gap:1.5rem; flex-wrap:wrap; }
  .fdtl-item { font-family:'Share Tech Mono',monospace; font-size:0.72rem; }
  .fdtl-ok   { color:#155724; }
  .fdtl-warn { color:#856404; }
  .fdtl-over { color:#721c24; font-weight:700; }
  .qual-row  { display:flex; gap:0.5rem; flex-wrap:wrap; margin-top:0.5rem; }
  .qual-tag  { font-family:'Share Tech Mono',monospace; font-size:0.65rem; padding:2px 8px; border-radius:10px; }
  .qual-ok   { background:#e8f5e9; color:#155724; border:1px solid #a5d6a7; }
  .qual-warn { background:#fff3cd; color:#856404; border:1px solid #ffc107; }
  .qual-exp  { background:#f8d7da; color:#721c24; border:1px solid #f5c6cb; }
  .next-legal { font-family:'Share Tech Mono',monospace; font-size:0.8rem; background:#e8f0fe; color:#1a237e; padding:0.5rem 1rem; border-radius:6px; margin-bottom:0.8rem; border-left:4px solid #1a237e; }
  .print-btn { display:inline-block; background:#1a1a2e; color:#fff; border:none; border-radius:5px; padding:6px 16px; font-size:0.75rem; cursor:pointer; font-family:'Share Tech Mono',monospace; letter-spacing:0.08em; margin-bottom:1rem; }
  @media print { .stSidebar,.stButton,button,.print-btn,.stSelectbox { display:none !important; } }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">👤 Individual Crew View</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">COMPLIANCE & HR INTERFACE — MONTHLY DUTY CALENDAR — FDTL MONITORING</div>', unsafe_allow_html=True)

try:
    conn = get_connection()
    cur  = conn.cursor()

    # Crew selector
    cur.execute("SELECT id, full_name, role, employee_id FROM crew_master WHERE is_active=TRUE ORDER BY role, full_name")
    crew_list = cur.fetchall()
    crew_options = {f"{name} ({emp_id}) — {role}": (cid, name, role, emp_id) for cid, name, role, emp_id in crew_list}

    selected = st.selectbox("Select Crew Member", list(crew_options.keys()))
    crew_id, crew_name, crew_role, emp_id = crew_options[selected]

    today      = date.today()
    month_start = today.replace(day=1)
    month_end   = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Get duties this month
    cur.execute("""
        SELECT fs.flight_number, fs.departure_time::date, fs.departure_time, fs.arrival_time,
               fs.origin, fs.destination, r.is_manual_override
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        WHERE r.crew_id = %s AND fs.departure_time::date BETWEEN %s AND %s
        ORDER BY fs.departure_time
    """, (crew_id, month_start, month_end))
    duties = cur.fetchall()

    # FDTL stats
    cur.execute("SELECT COALESCE(SUM(total_duty_hours),0) FROM duty_log WHERE crew_id=%s AND duty_start >= %s", (crew_id, today - timedelta(days=7)))
    weekly_hrs = float(cur.fetchone()[0])

    cur.execute("SELECT COALESCE(SUM(total_duty_hours),0) FROM duty_log WHERE crew_id=%s AND duty_start >= %s", (crew_id, today - timedelta(days=28)))
    monthly_hrs = float(cur.fetchone()[0])

    cur.execute("SELECT MAX(duty_end) FROM duty_log WHERE crew_id=%s", (crew_id,))
    last_end = cur.fetchone()[0]

    # Qualifications
    try:
        cur.execute("SELECT qualification_type, expiry_date FROM crew_qualifications WHERE crew_id=%s ORDER BY expiry_date", (crew_id,))
        quals = cur.fetchall()
    except:
        quals = []

    cur.close()
    conn.close()

    # ── Profile card ──────────────────────────────────────────────────────────
    role_badge = f'<span class="profile-role-{"lcc" if crew_role=="LCC" else "cc"}">{crew_role}</span>'
    total_flights = len(duties)
    total_hours   = sum((arr - dep).total_seconds()/3600 for _, _, dep, arr, *_ in duties)

    st.markdown(f"""
    <div class="crew-profile">
      <div>
        <div class="profile-name">{crew_name}</div>
        <div style="margin-top:4px">{role_badge} &nbsp; <span style="font-family:'Share Tech Mono',monospace;font-size:0.7rem;color:#888">{emp_id}</span></div>
      </div>
      <div class="profile-stat"><div class="profile-stat-val">{total_flights}</div><div class="profile-stat-lbl">Flights This Month</div></div>
      <div class="profile-stat"><div class="profile-stat-val">{total_hours:.1f}h</div><div class="profile-stat-lbl">Duty Hours This Month</div></div>
      <div class="profile-stat"><div class="profile-stat-val">{weekly_hrs:.1f}h</div><div class="profile-stat-lbl">Last 7 Days</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Next legal report time ────────────────────────────────────────────────
    if last_end:
        next_legal = last_end + timedelta(hours=12)
        if next_legal > today.replace(hour=0) if hasattr(today, 'hour') else True:
            st.markdown(f'<div class="next-legal">⏰ Next Legal Report Time: {next_legal.strftime("%d %b %Y at %H:%M")}</div>', unsafe_allow_html=True)

    # ── FDTL Summary ──────────────────────────────────────────────────────────
    def fdtl_class(val, warn, limit):
        if val >= limit: return "fdtl-over"
        if val >= warn:  return "fdtl-warn"
        return "fdtl-ok"

    st.markdown(f"""
    <div class="fdtl-bar">
      <div style="font-family:'Orbitron',monospace;font-size:0.65rem;color:#888;margin-bottom:0.4rem;letter-spacing:0.1em">FDTL STATUS</div>
      <div class="fdtl-row">
        <span class="fdtl-item {fdtl_class(weekly_hrs, 35, 40)}">7-DAY: {weekly_hrs:.1f}h / 40h</span>
        <span class="fdtl-item {fdtl_class(monthly_hrs, 85, 100)}">28-DAY: {monthly_hrs:.1f}h / 100h</span>
        <span class="fdtl-item {fdtl_class(total_hours, 85, 100)}">MONTH: {total_hours:.1f}h / 100h</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Qualifications ────────────────────────────────────────────────────────
    if quals:
        qual_html = '<div class="qual-row">'
        for qt, exp in quals:
            days_left = (exp - today).days
            if days_left < 0:
                cls, tag = "qual-exp", f"🔴 {qt}: EXPIRED {exp.strftime('%d %b %y')}"
            elif days_left <= 30:
                cls, tag = "qual-warn", f"🟡 {qt}: {exp.strftime('%d %b %y')} ({days_left}d)"
            else:
                cls, tag = "qual-ok", f"✅ {qt}: {exp.strftime('%d %b %y')}"
            qual_html += f'<span class="qual-tag {cls}">{tag}</span>'
        qual_html += '</div>'
        st.markdown(qual_html, unsafe_allow_html=True)
        st.markdown("")

    # ── Monthly Calendar ──────────────────────────────────────────────────────
    duty_by_date = {}
    for fn, dt, dep, arr, orig, dest, override in duties:
        hrs = (arr - dep).total_seconds() / 3600
        duty_by_date.setdefault(dt, []).append((fn, hrs, orig, dest))

    # Calendar header
    cal_html = '<div class="cal-grid">'
    for day in ["MON","TUE","WED","THU","FRI","SAT","SUN"]:
        cal_html += f'<div class="cal-header">{day}</div>'

    # Padding for first day
    first_weekday = month_start.weekday()
    for _ in range(first_weekday):
        cal_html += '<div></div>'

    current = month_start
    while current <= month_end:
        is_today = current == today
        day_duties = duty_by_date.get(current, [])
        day_class  = "duty" if day_duties else "rest"
        if is_today: day_class += " today"

        flights_html = ""
        for fn, hrs, orig, dest in day_duties:
            flights_html += f'<div class="cal-flights">{fn}</div><div class="cal-hours">{orig}→{dest} {hrs:.1f}h</div>'

        cal_html += f"""
        <div class="cal-day {day_class}">
          <div class="cal-date">{current.day}</div>
          {flights_html if flights_html else '<div class="cal-hours" style="color:#ccc">—</div>'}
        </div>"""
        current += timedelta(days=1)

    cal_html += '</div>'
    st.markdown(cal_html, unsafe_allow_html=True)

    # Print + CSV
    st.markdown('<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>', unsafe_allow_html=True)

    import io
    csv_rows = [{"Flight": fn, "Date": str(dt), "Route": f"{orig}→{dest}",
                 "Hours": f"{(arr-dep).total_seconds()/3600:.1f}"}
                for fn, dt, dep, arr, orig, dest, _ in duties]
    csv_buf = io.StringIO()
    pd.DataFrame(csv_rows).to_csv(csv_buf, index=False)
    st.download_button("⬇️ Download CSV", csv_buf.getvalue(),
                       file_name=f"crew_{emp_id}_{month_start}.csv", mime="text/csv")

except Exception as e:
    st.error(f"Database error: {e}")
