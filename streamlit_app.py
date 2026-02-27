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
    "https://raw.githubusercontent.com/Najmi125/crew-roster/main/assets/cc.jpg",
    width=150
)
st.sidebar.title("✈️ XYZ Airlines")
st.sidebar.markdown("---")

st.title("✈ AI-Driven Crew Operations Optimization Platform")
st.markdown("**Validated on Model XYZ Airline · 3 Aircraft · 360 Monthly Flights · 75 Crew**")
st.markdown("---")

st.markdown("""
**Intelligent 30-Day Rolling Scheduling Architecture**

CAA Pakistan FDTL Compliant · Fully Customizable for Any Airline Scale and Parameters

Preserves complete human scheduling control while enabling instantaneous, compliance-aware roster re-optimization after any OCC modification.

---

**Strategic Value Additions**

- Equitable and transparent crew utilization metrics
- Real-time duty record ledger per crew member
- Automated legality enforcement with audit trail
- Data-driven workforce planning insights

---

*Use the sidebar to navigate between views.*
""")
