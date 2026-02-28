import streamlit as st
import os

if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
    os.environ['DATABASE_URL'] = st.secrets['DATABASE_URL']

st.set_page_config(
    page_title="XYZ Crew Operations Platform",
    page_icon="✈️",
    layout="wide"
)

st.sidebar.image(
    "https://raw.githubusercontent.com/Najmi125/crew-roster/main/assets/logo.png",
    use_container_width=True
)
st.sidebar.title("✈️ XYZ Airlines")
st.sidebar.markdown("---")

st.markdown("## **✈ AI-Driven Crew Operations Control Platform**")
st.markdown("Intelligent 30-Day Rolling Roster: Cabin Crew")
st.markdown("Live Demonstration Model — XYZ Airlines | 3 x A320 | 12 Daily Flights | 75 Crew Members")
st.markdown("CAA Pakistan FDTL–Compliant")

st.markdown("---")

st.markdown("**Scheduling Engine**")
st.markdown("""
- Continuous Legality Surveillance
- Full Human Command Authority Preserved (OCC Override / Crew Change)
- Instant Compliance-Aware Re-Optimization (updated subsequent roster)
""")

st.markdown("**Operational Control Intelligence**")
st.markdown("""
- Fair & Transparent Crew Duty Distribution
- Real-Time Duty & Rest Ledger (Per Crew Member)
- Automated Legality Enforcement with Full Audit Trail
- Workforce Capacity, Exposure & Risk Monitoring
""")

st.markdown("**Customization & Scalability**")
st.markdown("""
This platform is demonstrated on a live XYZ Airlines operational model — It is fully configurable
to your fleet composition, crew complement, network structure, regulatory environment,
and airline-specific operational requirements.
""")

st.markdown("**Fail Safe Operations**")
st.markdown("""
In the most unlikely possibility of a system failure, your airline will still have the next
30 days roster that could be kept operational manually, just like it is NOW.
""")

st.markdown("---")
st.markdown("*👈 Use the sidebar to navigate between views.*")
