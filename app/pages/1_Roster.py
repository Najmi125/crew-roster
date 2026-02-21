import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

st.title("📋 7-Day Roster View")

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

# Date range selector
col1, col2 = st.columns([2, 4])
with col1:
    start_date = st.date_input("From", value=date.today())

end_date = start_date + timedelta(days=6)
st.caption(f"Showing: {start_date} → {end_date}")
st.markdown("---")

try:
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT
            fs.departure_time::date        AS duty_date,
            fs.flight_number,
            fs.origin || '→' || fs.destination AS route,
            TO_CHAR(fs.departure_time, 'HH24:MI') AS dep,
            TO_CHAR(fs.arrival_time,   'HH24:MI') AS arr,
            fs.aircraft_type,
            cm.full_name,
            cm.role,
            cm.employee_id,
            r.is_manual_override
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        JOIN crew_master     cm ON cm.id = r.crew_id
        WHERE fs.departure_time::date BETWEEN %s AND %s
        ORDER BY fs.departure_time, cm.role DESC, cm.full_name
    """, (start_date, end_date))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        st.warning("No roster data found for this period.")
        st.stop()

    df = pd.DataFrame(rows, columns=[
        'Date','Flight','Route','Dep','Arr','Aircraft',
        'Crew','Role','EmpID','Override'
    ])

    # Group by date then flight
    for duty_date in sorted(df['Date'].unique()):
        day_df = df[df['Date'] == duty_date]
        st.subheader(f"📅 {duty_date.strftime('%A, %d %B %Y')}")

        for flight in sorted(day_df['Flight'].unique()):
            fl_df   = day_df[day_df['Flight'] == flight].iloc[0]
            crew_df = day_df[day_df['Flight'] == flight][['Crew','Role','EmpID','Override']]

            with st.expander(
                f"✈️ {flight}  |  {fl_df['Route']}  |  "
                f"{fl_df['Dep']}→{fl_df['Arr']}  |  {fl_df['Aircraft']}"
            ):
                for _, crew_row in crew_df.iterrows():
                    role_color = "🟡" if crew_row['Role'] == 'LCC' else "🔵"
                    override   = " ⚠️ *Manual Override*" if crew_row['Override'] else ""
                    st.markdown(
                        f"{role_color} **{crew_row['Role']}** — "
                        f"{crew_row['Crew']} ({crew_row['EmpID']}){override}"
                    )

        st.markdown("---")

except Exception as e:
    st.error(f"Error: {e}")



