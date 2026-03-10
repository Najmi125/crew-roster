import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from reopt_helper import reoptimize_from
    REOPT_AVAILABLE = True
except:
    REOPT_AVAILABLE = False

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

    # Ensure crew_leave table exists
    cur.execute(
        "CREATE TABLE IF NOT EXISTS crew_leave ("
        "id SERIAL PRIMARY KEY, crew_id INTEGER NOT NULL, "
        "leave_date DATE NOT NULL, leave_type VARCHAR(50) NOT NULL, "
        "notes TEXT, created_at TIMESTAMP DEFAULT NOW(), "
        "UNIQUE(crew_id, leave_date))"
    )
    conn.commit()

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

    # FDTL stats — past only for 7-day/28-day limits, full month for planning
    week_start   = today - timedelta(days=6)
    days28_start = today - timedelta(days=27)
    cur.execute("SELECT COALESCE(SUM(total_duty_hours),0) FROM duty_log WHERE crew_id=%s AND duty_start::date BETWEEN %s AND %s", (crew_id, week_start, today))
    weekly_hrs = float(cur.fetchone()[0])
    cur.execute("SELECT COALESCE(SUM(total_duty_hours),0) FROM duty_log WHERE crew_id=%s AND duty_start::date BETWEEN %s AND %s", (crew_id, days28_start, today))
    monthly_hrs = float(cur.fetchone()[0])
    cur.execute("SELECT MAX(duty_end) FROM duty_log WHERE crew_id=%s AND duty_start::date <= %s", (crew_id, today))
    last_end = cur.fetchone()[0]

    # Last month date range
    last_month_end   = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    cur.execute(
        "SELECT COALESCE(dl.flight_number, fs.flight_number) as fn, "
        "dl.duty_start::date, dl.duty_start, dl.duty_end, "
        "COALESCE(dl.origin, fs.origin, '—') as orig, "
        "COALESCE(dl.destination, fs.destination, '—') as dest "
        "FROM duty_log dl "
        "LEFT JOIN flight_schedule fs ON fs.id = dl.flight_id "
        "WHERE dl.crew_id = %s AND dl.duty_start::date BETWEEN %s AND %s "
        "ORDER BY dl.duty_start",
        (crew_id, last_month_start, last_month_end)
    )
    last_month_duties = cur.fetchall()

    # Qualifications
    try:
        cur.execute("SELECT qualification_type, expiry_date FROM crew_qualifications WHERE crew_id=%s ORDER BY expiry_date", (crew_id,))
        quals = cur.fetchall()
    except:
        quals = []

    # Leave records
    try:
        cur.execute("SELECT leave_date, leave_type, notes FROM crew_leave WHERE crew_id=%s AND leave_date BETWEEN %s AND %s ORDER BY leave_date", (crew_id, month_start, month_end))
        leave_records = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    except:
        leave_records = {}

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
        st.markdown(f'<div class="next-legal">⏰ Next Legal Report Time: {next_legal.strftime("%d %b %Y at %H:%M")}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="next-legal">⏰ Next Legal Report Time: No completed duties on record</div>', unsafe_allow_html=True)

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

    # ── Last Month Consolidated Duty Log ─────────────────────────────────────
    st.markdown("---")
    st.markdown(f"#### 📋 Last Month Duty Log — {last_month_start.strftime('%B %Y')}")
    if not last_month_duties:
        st.info("No duties recorded for last month.")
    else:
        lm_sectors = len(last_month_duties)
        lm_hours   = sum((arr - dep).total_seconds()/3600 for _, _, dep, arr, *_ in last_month_duties)
        lm_routes  = list(dict.fromkeys(f"{orig}>{dest}" for _, _, _, _, orig, dest in last_month_duties))
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Sectors",    str(lm_sectors))
        col_b.metric("Total Duty Hours", f"{lm_hours:.1f}h")
        col_c.metric("Routes Flown",     str(len(lm_routes)))
        lm_rows = [{"Flight": fn, "Date": str(dt), "Route": f"{orig}>{dest}",
                    "Dep": dep.strftime('%H:%M'), "Arr": arr.strftime('%H:%M'),
                    "Hours": f"{(arr-dep).total_seconds()/3600:.1f}h"}
                   for fn, dt, dep, arr, orig, dest in last_month_duties]
        st.dataframe(pd.DataFrame(lm_rows), use_container_width=True, hide_index=True)
    st.markdown("---")

    # Print + CSV

    import io
    lm_csv_rows = [{"Flight": fn, "Date": str(dt), "Route": f"{orig}→{dest}",
                    "Dep": dep.strftime("%H:%M"), "Arr": arr.strftime("%H:%M"),
                    "Hours": f"{(arr-dep).total_seconds()/3600:.1f}"}
                   for fn, dt, dep, arr, orig, dest in last_month_duties] if last_month_duties else []
    csv_buf = io.StringIO()
    pd.DataFrame(lm_csv_rows).to_csv(csv_buf, index=False)
    st.download_button("⬇️ Download Last Month CSV", csv_buf.getvalue(),
                       file_name=f"crew_{emp_id}_{last_month_start.strftime('%Y-%m')}.csv", mime="text/csv")

    # ── Leave Management ──────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📅 OCC LEAVE MANAGEMENT"):
        st.markdown(f"**{crew_name}**")
        lv1, lv2, lv3 = st.columns(3)
        with lv1:
            lv_from = st.date_input("From", value=date.today(), key="lv_from")
        with lv2:
            lv_to   = st.date_input("To",   value=date.today(), key="lv_to")
        with lv3:
            lv_type = st.selectbox("Type", ["Annual Leave","Sick Leave","Training","Standby"], key="lv_type")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Set Leave", key="btn_set_leave", use_container_width=True):
                if lv_to < lv_from:
                    st.error("'To' must be on or after 'From'.")
                else:
                    try:
                        conn_l = get_connection(); cur_l = conn_l.cursor()
                        d = lv_from
                        while d <= lv_to:
                            cur_l.execute(
                                "INSERT INTO crew_leave (crew_id,leave_date,leave_type) VALUES (%s,%s,%s) "
                                "ON CONFLICT (crew_id,leave_date) DO UPDATE SET leave_type=EXCLUDED.leave_type",
                                (crew_id, d, lv_type))
                            cur_l.execute("DELETE FROM roster WHERE crew_id=%s AND duty_date=%s", (crew_id, d))
                            d += timedelta(days=1)
                        conn_l.commit(); cur_l.close(); conn_l.close()
                        days = (lv_to - lv_from).days + 1
                        st.success(f"✅ {lv_type} set: {lv_from.strftime('%d %b')} – {lv_to.strftime('%d %b')} ({days} days) — {crew_name} removed from all flights in this period")
                        st.rerun()
                    except Exception as e2:
                        st.error(f"Error: {e2}")
        with c2:
            if st.button("🗑️ Clear Leave", key="btn_clear_leave", use_container_width=True):
                try:
                    conn_l = get_connection(); cur_l = conn_l.cursor()
                    cur_l.execute("DELETE FROM crew_leave WHERE crew_id=%s AND leave_date BETWEEN %s AND %s", (crew_id, lv_from, lv_to))
                    conn_l.commit(); cur_l.close(); conn_l.close()
                    st.success(f"✅ Leave cleared: {lv_from.strftime('%d %b')} – {lv_to.strftime('%d %b')} — run optimizer to reassign flights")
                    st.rerun()
                except Exception as e2:
                    st.error(f"Error: {e2}")

        if leave_records:
            st.markdown("**Current leave this month:**")
            rows_lv = [{"Date": str(d), "Type": v[0]} for d,v in sorted(leave_records.items())]
            st.dataframe(pd.DataFrame(rows_lv), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Database error: {e}")
