import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
import io
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'engine'))
try:
    from optimizer import reoptimize_from
    REOPT_AVAILABLE = True
except:
    REOPT_AVAILABLE = False

load_dotenv()

st.set_page_config(page_title="Daily Operations", page_icon="⚡", layout="wide")

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
  .flight-card { background:#fff; border:1px solid #e0e6f0; border-radius:8px; padding:0.9rem 1.2rem; margin-bottom:0.6rem; border-left:5px solid #1a1a2e; box-shadow:0 1px 6px rgba(0,0,0,0.06); }
  .flight-card.legal    { border-left-color:#28a745; }
  .flight-card.at-risk  { border-left-color:#f59e0b; }
  .flight-card.override { border-left-color:#dc3545; }
  .flight-card.cancelled{ border-left-color:#aaa; background:#f7f7f7; opacity:0.7; }
  .card-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; }
  .card-flight { font-family:'Orbitron',monospace; font-size:0.9rem; font-weight:700; color:#1a1a2e; }
  .card-route  { font-family:'Exo 2',sans-serif; font-size:0.8rem; color:#555; }
  .card-time   { font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#1a1a2e; background:#f0f4ff; padding:3px 8px; border-radius:4px; }
  .status-badge { font-family:'Share Tech Mono',monospace; font-size:0.62rem; padding:2px 8px; border-radius:10px; font-weight:bold; }
  .status-legal   { background:#d4edda; color:#155724; }
  .status-risk    { background:#fff3cd; color:#856404; }
  .status-override{ background:#f8d7da; color:#721c24; }
  .status-cancel  { background:#e2e3e5; color:#383d41; }
  .crew-row { display:flex; flex-wrap:wrap; gap:0.4rem; margin-top:0.4rem; }
  .crew-tag { font-family:'Exo 2',sans-serif; font-size:0.72rem; padding:2px 8px; border-radius:12px; }
  .crew-lcc { background:#fff3e0; color:#b35900; border:1px solid #ffcc80; font-weight:700; }
  .crew-cc  { background:#e8f5e9; color:#155724; border:1px solid #a5d6a7; }
  .crew-exp { border-color:#ef9a9a !important; color:#b71c1c !important; }
  .day-header { font-family:'Orbitron',monospace; font-size:0.75rem; color:#1a1a2e; letter-spacing:0.15em; text-transform:uppercase; background:#f7f8fc; padding:0.4rem 0.8rem; border-radius:4px; margin:1rem 0 0.6rem; border-left:4px solid #f59e0b; }
  .occ-panel { background:#f7f8fc; border:1px solid #e0e6f0; border-radius:8px; padding:1rem 1.2rem; margin-bottom:1rem; border-top:3px solid #1a1a2e; }
  .occ-title { font-family:'Orbitron',monospace; font-size:0.75rem; color:#1a1a2e; letter-spacing:0.12em; margin-bottom:0.8rem; }
  .print-btn { display:inline-block; background:#1a1a2e; color:#fff; border:none; border-radius:5px; padding:6px 16px; font-size:0.75rem; cursor:pointer; font-family:'Share Tech Mono',monospace; letter-spacing:0.08em; margin-bottom:1rem; }
  @media print { .stSidebar,.stButton,button,.print-btn { display:none !important; } }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">⚡ Daily Operations & OCC Control</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">LIVE OCC TACTICAL SCREEN — TODAY + NEXT 48 HOURS — CREW CHANGE · CANCEL · AD-HOC · RETIME</div>', unsafe_allow_html=True)

# ── OCC ACTION PANELS ─────────────────────────────────────────────────────────
with st.expander("🔧 OCC OVERRIDE CONTROLS", expanded=False):
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Crew Change", "❌ Cancel Flight", "✈️ Add Ad-hoc Flight", "🕐 Change Flight Times"])

    # ── TAB 1: CREW CHANGE ────────────────────────────────────────────────────
    with tab1:
        st.markdown('<div class="occ-title">CREW CHANGE — REPLACE A CREW MEMBER ON A FLIGHT</div>', unsafe_allow_html=True)
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT DISTINCT fs.flight_number, fs.departure_time::date FROM flight_schedule fs JOIN roster r ON r.flight_id = fs.id WHERE fs.departure_time::date BETWEEN %s AND %s ORDER BY fs.departure_time::date, fs.flight_number", (date.today(), date.today() + timedelta(days=2)))
            flight_options = [f"{r[0]} — {r[1].strftime('%d %b')}" for r in cur.fetchall()]
            cur.close(); conn.close()
        except: flight_options = []

        cc1, cc2 = st.columns(2)
        with cc1:
            selected_flight_cc = st.selectbox("Flight", flight_options, key="cc_flight")
        with cc2:
            if selected_flight_cc:
                fn, fd = selected_flight_cc.split(" — ")
                fd = datetime.strptime(fd, "%d %b").replace(year=date.today().year).date()
                try:
                    conn = get_connection(); cur = conn.cursor()
                    cur.execute("SELECT cm.id, cm.full_name, cm.role FROM roster r JOIN flight_schedule fs ON fs.id=r.flight_id JOIN crew_master cm ON cm.id=r.crew_id WHERE fs.flight_number=%s AND fs.departure_time::date=%s", (fn, fd))
                    current_crew = cur.fetchall()
                    cur.close(); conn.close()
                    remove_options = {f"[{r[2]}] {r[1]}": r[0] for r in current_crew}
                except: remove_options = {}
                crew_to_remove = st.selectbox("Remove Crew", list(remove_options.keys()), key="cc_remove")

        cc3, cc4 = st.columns(2)
        with cc3:
            try:
                conn = get_connection(); cur = conn.cursor()
                cur.execute("SELECT id, full_name, role FROM crew_master WHERE is_active=TRUE ORDER BY role, full_name")
                all_crew = cur.fetchall()
                cur.close(); conn.close()
                add_options = {f"[{r[2]}] {r[1]}": r[0] for r in all_crew}
            except: add_options = {}
            crew_to_add = st.selectbox("Add Crew", list(add_options.keys()), key="cc_add")
        with cc4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ Apply Crew Change", key="btn_cc"):
                try:
                    conn = get_connection(); cur = conn.cursor()
                    cur.execute("SELECT fs.id FROM flight_schedule fs WHERE fs.flight_number=%s AND fs.departure_time::date=%s", (fn, fd))
                    fid = cur.fetchone()[0]
                    remove_id = remove_options[crew_to_remove]
                    add_id    = add_options[crew_to_add]
                    cur.execute("DELETE FROM roster WHERE flight_id=%s AND crew_id=%s", (fid, remove_id))
                    cur.execute("INSERT INTO roster (flight_id, crew_id, duty_date, is_manual_override) VALUES (%s,%s,%s,TRUE) ON CONFLICT DO NOTHING", (fid, add_id, fd))
                    cur.execute("INSERT INTO legality_violations (flight_id, crew_id, violation_type, details) VALUES (%s,%s,%s,%s)", (fid, add_id, 'MANUAL_CREW_CHANGE', f'OCC replaced crew on {fn} {fd}'))
                    conn.commit(); cur.close(); conn.close()
                    st.success(f"✅ Crew changed on {fn} ({fd.strftime('%d %b')})")
                    if REOPT_AVAILABLE:
                        try:
                            n = reoptimize_from(fd)
                            st.info(f"🔄 Roster re-optimized: {n} assignments updated from {fd.strftime('%d %b')}")
                        except Exception as re:
                            st.warning(f"Roster re-optimization skipped: {re}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── TAB 2: CANCEL FLIGHT ──────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="occ-title">CANCEL FLIGHT — REMOVE ALL CREW ASSIGNMENTS</div>', unsafe_allow_html=True)
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT DISTINCT fs.flight_number, fs.departure_time::date FROM flight_schedule fs JOIN roster r ON r.flight_id=fs.id WHERE fs.departure_time::date BETWEEN %s AND %s ORDER BY fs.departure_time::date, fs.flight_number", (date.today(), date.today() + timedelta(days=2)))
            cancel_options = [f"{r[0]} — {r[1].strftime('%d %b')}" for r in cur.fetchall()]
            cur.close(); conn.close()
        except: cancel_options = []

        ca1, ca2 = st.columns([2,1])
        with ca1:
            selected_cancel = st.selectbox("Select Flight to Cancel", cancel_options, key="cancel_flight")
        with ca2:
            cancel_reason = st.text_input("Reason", placeholder="e.g. Weather, Technical", key="cancel_reason")

        if st.button("❌ Cancel Flight", key="btn_cancel"):
            if selected_cancel:
                fn_c, fd_c = selected_cancel.split(" — ")
                fd_c = datetime.strptime(fd_c, "%d %b").replace(year=date.today().year).date()
                try:
                    conn = get_connection(); cur = conn.cursor()
                    cur.execute("SELECT id FROM flight_schedule WHERE flight_number=%s AND departure_time::date=%s", (fn_c, fd_c))
                    fid_c = cur.fetchone()[0]
                    cur.execute("DELETE FROM roster WHERE flight_id=%s", (fid_c,))
                    cur.execute("INSERT INTO legality_violations (flight_id, crew_id, violation_type, details) VALUES (%s,NULL,%s,%s)", (fid_c, 'FLIGHT_CANCELLED', f'OCC cancelled {fn_c} on {fd_c} — {cancel_reason}'))
                    conn.commit(); cur.close(); conn.close()
                    st.success(f"✅ {fn_c} on {fd_c.strftime('%d %b')} cancelled")
                    if REOPT_AVAILABLE:
                        try:
                            n = reoptimize_from(fd_c)
                            st.info(f"🔄 Roster re-optimized: {n} assignments updated from {fd_c.strftime('%d %b')}")
                        except Exception as re:
                            st.warning(f"Roster re-optimization skipped: {re}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── TAB 3: ADD AD-HOC FLIGHT ──────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="occ-title">ADD AD-HOC FLIGHT — CREATE & ASSIGN CREW</div>', unsafe_allow_html=True)
        ah1, ah2, ah3 = st.columns(3)
        with ah1:
            ah_fn   = st.text_input("Flight Number", placeholder="e.g. XYZ999", key="ah_fn")
            ah_orig = st.text_input("Origin", placeholder="e.g. KHI", key="ah_orig").upper()
            ah_dest = st.text_input("Destination", placeholder="e.g. ISB", key="ah_dest").upper()
        with ah2:
            ah_date = st.date_input("Date", value=date.today(), key="ah_date")
            ah_dep  = st.time_input("Departure Time", key="ah_dep")
            ah_arr  = st.time_input("Arrival Time", key="ah_arr")
        with ah3:
            try:
                conn = get_connection(); cur = conn.cursor()
                cur.execute("SELECT id, full_name, role FROM crew_master WHERE is_active=TRUE AND role='LCC' ORDER BY full_name")
                lcc_opts = {f"{r[1]}": r[0] for r in cur.fetchall()}
                cur.execute("SELECT id, full_name, role FROM crew_master WHERE is_active=TRUE AND role='CC' ORDER BY full_name")
                cc_opts  = {f"{r[1]}": r[0] for r in cur.fetchall()}
                cur.close(); conn.close()
            except: lcc_opts = {}; cc_opts = {}
            ah_lcc  = st.selectbox("Assign LCC", list(lcc_opts.keys()), key="ah_lcc")
            ah_ccs  = st.multiselect("Assign CC (select 3)", list(cc_opts.keys()), key="ah_ccs")

        if st.button("✈️ Create Ad-hoc Flight", key="btn_adhoc"):
            if ah_fn and ah_orig and ah_dest and len(ah_ccs) == 3:
                try:
                    conn = get_connection(); cur = conn.cursor()
                    dep_dt = datetime.combine(ah_date, ah_dep)
                    arr_dt = datetime.combine(ah_date, ah_arr)
                    cur.execute("INSERT INTO flight_schedule (flight_number, origin, destination, departure_time, arrival_time, aircraft_type) VALUES (%s,%s,%s,%s,%s,'A320') RETURNING id", (ah_fn, ah_orig, ah_dest, dep_dt, arr_dt))
                    new_fid = cur.fetchone()[0]
                    all_crew = [lcc_opts[ah_lcc]] + [cc_opts[c] for c in ah_ccs]
                    for cid in all_crew:
                        cur.execute("INSERT INTO roster (flight_id, crew_id, duty_date, is_manual_override) VALUES (%s,%s,%s,TRUE)", (new_fid, cid, ah_date))
                        hours = (arr_dt - dep_dt).total_seconds() / 3600
                        cur.execute("INSERT INTO duty_log (crew_id, flight_id, duty_start, duty_end, total_duty_hours) VALUES (%s,%s,%s,%s,%s)", (cid, new_fid, dep_dt, arr_dt, hours))
                    cur.execute("INSERT INTO legality_violations (flight_id, crew_id, violation_type, details) VALUES (%s,NULL,'AD_HOC_FLIGHT',%s)", (new_fid, f'OCC added ad-hoc flight {ah_fn} {ah_orig}-{ah_dest} on {ah_date}'))
                    conn.commit(); cur.close(); conn.close()
                    st.success(f"✅ Ad-hoc flight {ah_fn} created and crew assigned")
                    if REOPT_AVAILABLE:
                        try:
                            n = reoptimize_from(ah_date)
                            st.info(f"🔄 Roster re-optimized: {n} assignments updated from {ah_date.strftime('%d %b')}")
                        except Exception as re:
                            st.warning(f"Roster re-optimization skipped: {re}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please fill all fields and select exactly 3 CC.")

    # ── TAB 4: CHANGE FLIGHT TIMES ────────────────────────────────────────────
    with tab4:
        st.markdown('<div class="occ-title">RETIME FLIGHT — UPDATE DEPARTURE / ARRIVAL TIMES</div>', unsafe_allow_html=True)
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT DISTINCT fs.flight_number, fs.departure_time::date, fs.departure_time, fs.arrival_time FROM flight_schedule fs WHERE fs.departure_time::date BETWEEN %s AND %s ORDER BY fs.departure_time::date, fs.flight_number", (date.today(), date.today() + timedelta(days=2)))
            retime_rows = cur.fetchall()
            cur.close(); conn.close()
            retime_options = {f"{r[0]} — {r[1].strftime('%d %b')}": r for r in retime_rows}
        except: retime_options = {}

        rt1, rt2, rt3 = st.columns(3)
        with rt1:
            selected_rt = st.selectbox("Select Flight", list(retime_options.keys()), key="rt_flight")
        if selected_rt and retime_options:
            _, _, cur_dep, cur_arr = retime_options[selected_rt]
            with rt2:
                new_dep = st.time_input("New Departure", value=cur_dep.time(), key="rt_dep")
            with rt3:
                new_arr = st.time_input("New Arrival", value=cur_arr.time(), key="rt_arr")

            if st.button("🕐 Update Times", key="btn_retime"):
                try:
                    fn_rt, fd_rt = selected_rt.split(" — ")
                    fd_rt = datetime.strptime(fd_rt, "%d %b").replace(year=date.today().year).date()
                    new_dep_dt = datetime.combine(fd_rt, new_dep)
                    new_arr_dt = datetime.combine(fd_rt, new_arr)
                    conn = get_connection(); cur = conn.cursor()
                    cur.execute("UPDATE flight_schedule SET departure_time=%s, arrival_time=%s WHERE flight_number=%s AND departure_time::date=%s", (new_dep_dt, new_arr_dt, fn_rt, fd_rt))
                    cur.execute("SELECT id FROM flight_schedule WHERE flight_number=%s AND departure_time::date=%s", (fn_rt, fd_rt))
                    fid_rt = cur.fetchone()[0]
                    cur.execute("INSERT INTO legality_violations (flight_id, crew_id, violation_type, details) VALUES (%s,NULL,'FLIGHT_RETIMED',%s)", (fid_rt, f'OCC retimed {fn_rt} on {fd_rt}: dep {new_dep} arr {new_arr}'))
                    conn.commit(); cur.close(); conn.close()
                    st.success(f"✅ {fn_rt} retimed to {new_dep}→{new_arr}")
                    if REOPT_AVAILABLE:
                        try:
                            n = reoptimize_from(fd_rt)
                            st.info(f"🔄 Roster re-optimized: {n} assignments updated from {fd_rt.strftime('%d %b')}")
                        except Exception as re:
                            st.warning(f"Roster re-optimization skipped: {re}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ── FLIGHT VIEW ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>', unsafe_allow_html=True)
csv_placeholder = st.empty()

try:
    conn = get_connection()
    cur  = conn.cursor()
    today    = date.today()
    end_view = today + timedelta(days=2)

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
        SELECT fs.flight_number, fs.origin, fs.destination,
               fs.departure_time, fs.arrival_time, fs.aircraft_type,
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

    # Get cancelled flights
    cur.execute("""
        SELECT DISTINCT fs.flight_number, fs.departure_time::date
        FROM flight_schedule fs
        JOIN legality_violations lv ON lv.flight_id = fs.id
        WHERE lv.violation_type = 'FLIGHT_CANCELLED'
        AND fs.departure_time::date BETWEEN %s AND %s
    """, (today, end_view))
    cancelled = {(r[0], r[1]) for r in cur.fetchall()}

    cur.close()
    conn.close()

    cols = ['flight_number','origin','destination','departure_time','arrival_time',
            'aircraft_type','duty_date','full_name','role','employee_id','crew_id','is_manual_override']
    df = pd.DataFrame(rows, columns=cols)

    # Also show flights with no crew (cancelled)
    conn2 = get_connection(); cur2 = conn2.cursor()
    cur2.execute("SELECT DISTINCT fs.flight_number, fs.origin, fs.destination, fs.departure_time, fs.arrival_time, fs.aircraft_type FROM flight_schedule fs WHERE fs.departure_time::date BETWEEN %s AND %s", (today, end_view))
    all_flights = cur2.fetchall()
    cur2.close(); conn2.close()

    csv_data = []
    for duty_date in sorted(set([r[3].date() for r in all_flights])):
        day_label = "TODAY" if duty_date == today else ("TOMORROW" if duty_date == today + timedelta(days=1) else duty_date.strftime("%A %d %b").upper())
        st.markdown(f'<div class="day-header">📅 {day_label} — {duty_date.strftime("%A, %d %B %Y")}</div>', unsafe_allow_html=True)

        day_flights = [r for r in all_flights if r[3].date() == duty_date]
        for flt in sorted(day_flights, key=lambda x: x[3]):
            flight_num = flt[0]
            is_cancelled = (flight_num, duty_date) in cancelled

            if is_cancelled:
                st.markdown(f"""
                <div class="flight-card cancelled">
                  <div class="card-header">
                    <div><span class="card-flight">{flight_num}</span>
                    <span class="card-route"> &nbsp;{flt[1]} → {flt[2]} &nbsp;·&nbsp; {flt[5]}</span></div>
                    <span class="status-badge status-cancel">❌ CANCELLED</span>
                  </div>
                </div>""", unsafe_allow_html=True)
                continue

            fl = df[(df['flight_number'] == flight_num) & (df['duty_date'] == duty_date)]
            if fl.empty: continue

            has_override = fl['is_manual_override'].any()
            has_exp      = fl['crew_id'].isin(expiring_crew_ids).any()

            if has_override:
                card_class, status_class, status_label = "override", "status-override", "⚠️ MANUAL OVERRIDE"
            elif has_exp:
                card_class, status_class, status_label = "at-risk",  "status-risk",     "🟡 AT RISK — QUAL EXPIRING"
            else:
                card_class, status_class, status_label = "legal",    "status-legal",    "✅ LEGAL"

            dep_str = flt[3].strftime('%H:%M')
            arr_str = flt[4].strftime('%H:%M')

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
                  <span class="card-route"> &nbsp;{flt[1]} → {flt[2]} &nbsp;·&nbsp; {flt[5]}</span>
                </div>
                <div style="display:flex;gap:0.5rem;align-items:center;">
                  <span class="card-time">{dep_str} → {arr_str}</span>
                  <span class="status-badge {status_class}">{status_label}</span>
                </div>
              </div>
              <div class="crew-row">{crew_tags}</div>
            </div>""", unsafe_allow_html=True)

            csv_data.append({'Date': duty_date, 'Flight': flight_num,
                'Route': f"{flt[1]}-{flt[2]}", 'Departure': dep_str, 'Arrival': arr_str,
                'Status': status_label.replace("✅ ","").replace("🟡 ","").replace("⚠️ ",""),
                'Crew': " | ".join(crew_csv)})

    if csv_data:
        csv_buf = io.StringIO()
        pd.DataFrame(csv_data).to_csv(csv_buf, index=False)
        csv_placeholder.download_button("⬇️ Download CSV", csv_buf.getvalue(),
            file_name=f"daily_ops_{today}.csv", mime="text/csv")

except Exception as e:
    st.error(f"Database error: {e}")
