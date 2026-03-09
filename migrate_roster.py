"""Run once to add is_manual_override column to roster table."""
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur  = conn.cursor()
cur.execute("""
    ALTER TABLE roster
    ADD COLUMN IF NOT EXISTS is_manual_override BOOLEAN DEFAULT FALSE
""")
conn.commit()
cur.close(); conn.close()
print("✅ roster.is_manual_override column added")
