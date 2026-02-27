import streamlit as st
import os

# Inject secrets as env vars for pages running via runpy
if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
    os.environ['DATABASE_URL'] = st.secrets['DATABASE_URL']

st.switch_page("pages/0_Dashboard.py")
