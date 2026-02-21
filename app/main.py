import streamlit as st
from dotenv import load_dotenv
import psycopg2
import os

load_dotenv()

# Page config
st.set_page_config(
    page_title="Crew Roster System",
    page_icon="✈️",
    layout="wide"
)

# DB connection
def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

# Sidebar
st.sidebar.image("https://raw.githubusercontent.com/Najmi125/crew-roster/main/assets/cc.jpg")
st.sidebar.title("✈️ Crew Roster")
st.sidebar.markdown("---")
mode = st.sidebar.radio("Mode", ["🟢 Live", "🧪 Simulation"])
st.sidebar.markdown("---")
st.sidebar.markdown("**OCC Decision Support**")

# Main header
st.title("✈️ AI Crew Roster System")
st.caption("Operational Control Centre — Decision Support Platform")
st.markdown("---")

# Stats row
col1, col2, col3, col4 = st.columns(4)
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
    cur.close()
    conn.close()
    with col1:
        st.metric("👨‍✈️ Active Crew", active_crew)
    with col2:
        st.metric("✈️ Flights Scheduled", total_flights)
    with col3:
        st.metric("📋 Assignments", total_assignments)
    with col4:
        st.metric("⚠️ Violations", violations, delta=None)
except Exception as e:
    st.error(f"Database connection error: {e}")

st.markdown("---")

# Mode indicator
if "Simulation" in mode:
    st.warning("🧪 SIMULATION MODE — No changes affect live roster")
else:
    st.success("🟢 LIVE MODE — Changes affect operational roster")

st.markdown("### 📋 Quick Status")
st.info("Use the sidebar to navigate to Roster View or Manual Override.")
