import os
import streamlit as st

# Re-inject secrets as env vars so runpy context can access them
if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
    os.environ['DATABASE_URL'] = st.secrets['DATABASE_URL']

import runpy
runpy.run_path("app/main.py")
