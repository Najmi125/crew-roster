import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Manual Override", page_icon="⚠️", layout="wide")
st.title("⚠️ Manual Override Panel")
st.caption("OCC Planner — Replace crew on any flight. All changes are logged.")

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

st.markdown("---")

# ── Step 1: Pick a date ───────────────────────────────────────────────────
selected_date = st.date_input("Select Duty Date", value=date.today())

conn = get_connection()
cur  = conn.cursor()

# ── Step 2: Pick a flight ─────────────────────────────────────────────────
cur.execute("""
    SELECT id, flight_number, origin, destination,
           TO_CHAR(departure_time,'HH24:MI') AS dep,
           TO_CHAR(arrival_time,  'HH24:MI') AS arr,
           departure_time, arrival_time
    FROM flight_schedule
    WHERE departure_time::date = %s
    ORDER BY departure_time
""", (selected_date,))
flights = cur.fetchall()

if not flights:
    st.warning("No flights found for this date.")
    st.stop()

flight_options = {
    f"{r[1]} | {r[2]}→{r[3]} | {r[4]}→{r[5]}": r
    for r in flights
}
selected_flight_label = st.selectbox("Select Flight", list(flight_options.keys()))
selected_flight       = flight_options[selected_flight_label]
flight_id             = selected_flight[0]
dep_time              = selected_flight[6]
arr_time              = selected_flight[7]

st.markdown("---")

# ── Step 3: Show current crew ─────────────────────────────────────────────
st.subheader("Current Crew Assignment")
cur.execute("""
    SELECT cm.id, cm.employee_id, cm.full_name, cm.role, r.id as roster_id
    FROM roster r
    JOIN crew_master cm ON cm.id = r.crew_id
    WHERE r.flight_id = %s
    ORDER BY cm.role DESC, cm.full_name
""", (flight_id,))
current_crew = cur.fetchall()

if not current_crew:
    st.warning("No crew assigned to this flight yet.")
    st.stop()

crew_options = {
    f"{r[3]} — {r[2]} ({r[1]})": r
    for r in current_crew
}

for label in crew_options:
    role = "🟡" if "LCC" in label else "🔵"
    st.markdown(f"{role} {label}")

st.markdown("---")

# ── Step 4: Select who to replace ────────────────────────────────────────
st.subheader("Replace a Crew Member")
crew_to_replace_label = st.selectbox("Who to replace?", list(crew_options.keys()))
crew_to_replace       = crew_options[crew_to_replace_label]
replace_role          = crew_to_replace[3]
roster_id_to_replace  = crew_to_replace[4]

# ── Step 5: Find legal replacements ──────────────────────────────────────
cur.execute("""
    SELECT cm.id, cm.employee_id, cm.full_name
    FROM crew_master cm
    WHERE cm.role = %s
    AND cm.is_active = TRUE
    AND cm.id NOT IN (
        SELECT crew_id FROM roster WHERE flight_id = %s
    )
    ORDER BY cm.full_name
""", (replace_role, flight_id))
available = cur.fetchall()

if not available:
    st.error("No available crew of same role found.")
    st.stop()

replacement_options = {
    f"{r[2]} ({r[1]})": r for r in available
}
selected_replacement_label = st.selectbox("Replace with", list(replacement_options.keys()))
selected_replacement       = replacement_options[selected_replacement_label]

# ── Step 6: Reason + confirm ──────────────────────────────────────────────
st.markdown("---")
override_reason  = st.text_input("Reason for override", placeholder="e.g. Sick call, training conflict...")
performed_by     = st.text_input("Your name / ID", placeholder="e.g. OCC/Ahmed")

if st.button("✅ Confirm Override", type="primary"):
    if not override_reason or not performed_by:
        st.error("Please fill in reason and your name before confirming.")
        st.stop()

    # Remove old assignment
    cur.execute("DELETE FROM roster WHERE id = %s", (roster_id_to_replace,))

    # Add new assignment
    cur.execute("""
        INSERT INTO roster (flight_id, crew_id, duty_date, is_manual_override, override_reason, override_by)
        VALUES (%s, %s, %s, TRUE, %s, %s)
    """, (flight_id, selected_replacement[0], selected_date, override_reason, performed_by))

    # Log to audit trail
    cur.execute("""
        INSERT INTO audit_trail (action, performed_by, target_table, old_value, new_value)
        VALUES ('MANUAL_OVERRIDE', %s, 'roster', %s, %s)
    """, (
        performed_by,
        f"{crew_to_replace[2]} on {selected_flight_label}",
        f"{selected_replacement[2]} on {selected_flight_label} — Reason: {override_reason}"
    ))

    conn.commit()

    st.success(f"✅ {crew_to_replace[2]} replaced by {selected_replacement[2]}")
    st.info(f"📋 Override logged to audit trail")
    st.balloons()

cur.close()

conn.close()
