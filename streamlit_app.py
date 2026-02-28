import streamlit as st
import os

if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
    os.environ['DATABASE_URL'] = st.secrets['DATABASE_URL']

st.switch_page("pages/1_Dashboard.py")
