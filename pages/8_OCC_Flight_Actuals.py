import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
import io
import os

load_dotenv()

st.set_page_config(page_title="Block time", page_icon="🛬", layout="wide")

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

def ensure_actuals_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flight_actuals (
            id               SERIAL PRIMARY KEY,
            flight_id        INTEGER NOT NULL,
            actual_block_off TIMESTAMP NOT NULL,
            actual_block_on  TIMESTAMP NOT NULL,
            entered_by       VARCHAR(100) DEFAULT 'OCC',
            entered_at       TIMESTAMP DEFAULT NOW(),
            notes            TEXT,
            UNIQUE(flight_id)
        )
    """)

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
  .actual-card { background:#fff; border:1px solid #e0e6f0; border-radius:8px; padding:0.9rem 1.2rem; margin-bottom:0.5rem; border-left:5px solid #1a1a2e; }
  .actual-card.has-actual { border-left-color:#28a745; background:#f0fff4; }
  .actual-card.no-actual  { border-left-color:#f59e0b; }
  .card-flight { font-family:'Orbitron',monospace; font-size:0.85rem; font-weight:700; color:#1a1a2e; }
  .card-route  { font-family:'Exo 2',sans-serif; font-size:0.78rem; color:#555; }
  .time-sched  { font-family:'Share Tech Mono',monospace; font-size:0.72rem; color:#888; }
  .time-actual { font-family:'Share Tech Mono',monospace; font-size:0.72rem; color:#155724; font-weight:700; }
  .day-header  { font-family:'Orbitron',monospace; font-size:0.75rem; color:#1a1a2e; letter-spacing:0.15em; background:#f7f8fc; padding:0.4rem 0.8rem; border-radius:4px; margin:1rem 0 0.5rem; border-left:4px solid #1a1a2e; }
  .badge-actual { background:#d4edda; color:#155724; font-family:'Share Tech Mono',monospace; font-size:0.6rem; padding:2px 8px; border-radius:10px; font-weight:700; }
  .badge-sched  { background:#fff3cd; color:#856404; font-family:'Share Tech Mono',monospace; font-size:0.6rem; padding:2px 8px; border-radius:10px; }
  .print-btn { display:inline-block; background:#1a1a2e; color:#fff; border:none; border-radius:5px; padding:6px 16px; font-size:0.75rem; cursor:pointer; font-family:'Share Tech Mono',monospace; letter-spacing:0.08em; margin-bottom:1rem; }
  @media print { .stSidebar,.stButton,button,.print-btn { display:none !important; } }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🛬 Block time</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">ENTER ACTUAL BLOCK OFF / BLOCK ON TIMES — OVERRIDES SCHEDULED TIMES IN ALL FDTL CALCULATIONS</div>', unsafe_allow_html=True)

# ── Date selector ─────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 4])
with col1:
    view_date = st.date_input("Date", value=date.today() - timedelta(days=1), label_visibility="collapsed")
    st.caption("Select date")

st.markdown('<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>', unsafe_allow_html=True)
csv_placeholder = st.empty()

try:
    conn = get_connection()
    cur  = conn.cursor()
    ensure_actuals_table(cur)
    conn.commit()

    # Load all flights for selected date
    cur.execute("""
        SELECT fs.id, fs.flight_number, fs.origin, fs.destination,
               fs.departure_time, fs.arrival_time
        FROM flight_schedule fs
        WHERE fs.departure_time::date = %s
        ORDER BY fs.departure_time
    """, (view_date,))
    flights = cur.fetchall()

    # Load existing actuals
    cur.execute("""
        SELECT flight_id, actual_block_off, actual_block_on, entered_by, notes
        FROM flight_actuals
        WHERE actual_block_off::date = %s
    """, (view_date,))
    actuals_map = {r[0]: r for r in cur.fetchall()}

    cur.close()
    conn.close()

    if not flights:
        st.warning(f"No flights found for {view_date.strftime('%d %B %Y')}.")
    else:
        st.markdown(f'<div class="day-header">📅 {view_date.strftime("%A, %d %B %Y")} — {len(flights)} Flights</div>', unsafe_allow_html=True)

        # Summary
        n_actual = len([f for f in flights if f[0] in actuals_map])
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Flights", len(flights))
        c2.metric("Actuals Entered", n_actual)
        c3.metric("Pending", len(flights) - n_actual)

        st.markdown("---")

        csv_rows = []
        for fid, fn, orig, dest, sched_dep, sched_arr in flights:
            has_actual = fid in actuals_map
            card_class = "has-actual" if has_actual else "no-actual"
            badge      = '<span class="badge-actual">✅ ACTUAL</span>' if has_actual else '<span class="badge-sched">🕐 SCHEDULED</span>'

            sched_dep_str = sched_dep.strftime('%H:%M')
            sched_arr_str = sched_arr.strftime('%H:%M')

            if has_actual:
                act = actuals_map[fid]
                act_dep_str = act[1].strftime('%H:%M')
                act_arr_str = act[2].strftime('%H:%M')
                block_time  = (act[2] - act[1]).total_seconds() / 3600
                delay_min   = int((act[1] - sched_dep).total_seconds() / 60)
                delay_str   = f"+{delay_min}min late" if delay_min > 0 else (f"{abs(delay_min)}min early" if delay_min < 0 else "On time")
                time_display = f'<span class="time-actual">Actual: {act_dep_str} → {act_arr_str} ({block_time:.1f}h) · {delay_str}</span>'
                notes_display = f" · {act[4]}" if act[4] else ""
            else:
                act_dep_str = sched_dep_str
                act_arr_str = sched_arr_str
                time_display = ""
                notes_display = ""

            st.markdown(f"""
            <div class="actual-card {card_class}">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <span class="card-flight">{fn}</span>
                  <span class="card-route"> &nbsp;{orig} → {dest}</span>
                  &nbsp;{badge}
                </div>
                <span class="time-sched">Sched: {sched_dep_str} → {sched_arr_str}</span>
              </div>
              {f'<div style="margin-top:4px">{time_display}{notes_display}</div>' if has_actual else ''}
            </div>
            """, unsafe_allow_html=True)

            # Entry form
            with st.expander(f"{'✏️ Edit' if has_actual else '➕ Enter'} Actuals — {fn} {orig}→{dest}"):
                f1, f2, f3 = st.columns(3)
                with f1:
                    default_dep = actuals_map[fid][1].strftime('%H:%M') if has_actual else sched_dep.strftime('%H:%M')
                    dep_str_in = st.text_input("Block Off — Actual Dep (HH:MM)", value=default_dep, key=f"dep_{fid}")
                with f2:
                    default_arr = actuals_map[fid][2].strftime('%H:%M') if has_actual else sched_arr.strftime('%H:%M')
                    arr_str_in = st.text_input("Block On — Actual Arr (HH:MM)", value=default_arr, key=f"arr_{fid}")
                with f3:
                    default_notes = actuals_map[fid][4] if has_actual else ""
                    notes = st.text_input("Notes (optional)", value=default_notes, placeholder="e.g. Delayed - ATC hold", key=f"notes_{fid}")

                bf1, bf2 = st.columns([1, 3])
                with bf1:
                    if st.button(f"💾 Save Actuals", key=f"save_{fid}"):
                        try:
                            block_off_dt = datetime.combine(view_date, datetime.strptime(dep_str_in, '%H:%M').time())
                            block_on_dt  = datetime.combine(view_date, datetime.strptime(arr_str_in, '%H:%M').time())
                            conn2 = get_connection()
                            cur2  = conn2.cursor()
                            ensure_actuals_table(cur2)
                            cur2.execute("""
                                INSERT INTO flight_actuals (flight_id, actual_block_off, actual_block_on, notes)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (flight_id) DO UPDATE
                                SET actual_block_off = EXCLUDED.actual_block_off,
                                    actual_block_on  = EXCLUDED.actual_block_on,
                                    notes            = EXCLUDED.notes,
                                    entered_at       = NOW()
                            """, (fid, block_off_dt, block_on_dt, notes))
                            # Update duty_log with actual times
                            actual_hours = (block_on_dt - block_off_dt).total_seconds() / 3600
                            cur2.execute("""
                                UPDATE duty_log
                                SET duty_start = %s, duty_end = %s, total_duty_hours = %s
                                WHERE flight_id = %s
                            """, (block_off_dt, block_on_dt, actual_hours, fid))
                            conn2.commit()
                            cur2.close(); conn2.close()
                            st.success(f"✅ Actuals saved for {fn}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with bf2:
                    if has_actual and st.button(f"🗑️ Clear Actuals (use scheduled)", key=f"clear_{fid}"):
                        try:
                            conn3 = get_connection(); cur3 = conn3.cursor()
                            cur3.execute("DELETE FROM flight_actuals WHERE flight_id=%s", (fid,))
                            # Restore scheduled times in duty_log
                            sched_hours = (sched_arr - sched_dep).total_seconds() / 3600
                            cur3.execute("UPDATE duty_log SET duty_start=%s, duty_end=%s, total_duty_hours=%s WHERE flight_id=%s", (sched_dep, sched_arr, sched_hours, fid))
                            conn3.commit(); cur3.close(); conn3.close()
                            st.success(f"✅ Actuals cleared — scheduled times restored")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            csv_rows.append({
                'Flight': fn, 'Route': f"{orig}-{dest}",
                'Sched Dep': sched_dep_str, 'Sched Arr': sched_arr_str,
                'Actual Dep': act_dep_str, 'Actual Arr': act_arr_str,
                'Status': 'ACTUAL' if has_actual else 'SCHEDULED'
            })

        # CSV
        csv_buf = io.StringIO()
        pd.DataFrame(csv_rows).to_csv(csv_buf, index=False)
        csv_placeholder.download_button("⬇️ Download CSV", csv_buf.getvalue(),
            file_name=f"actuals_{view_date}.csv", mime="text/csv")

except Exception as e:
    st.error(f"Database error: {e}")
