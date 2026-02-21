import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# 1. Crew Master
cur.execute("""
CREATE TABLE IF NOT EXISTS crew_master (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('LCC', 'CC')),
    whatsapp_number VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
""")

# 2. Flight Schedule
cur.execute("""
CREATE TABLE IF NOT EXISTS flight_schedule (
    id SERIAL PRIMARY KEY,
    flight_number VARCHAR(20) NOT NULL,
    origin VARCHAR(10) NOT NULL,
    destination VARCHAR(10) NOT NULL,
    departure_time TIMESTAMP NOT NULL,
    arrival_time TIMESTAMP NOT NULL,
    aircraft_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
""")

# 3. Roster
cur.execute("""
CREATE TABLE IF NOT EXISTS roster (
    id SERIAL PRIMARY KEY,
    flight_id INTEGER REFERENCES flight_schedule(id),
    crew_id INTEGER REFERENCES crew_master(id),
    duty_date DATE NOT NULL,
    is_manual_override BOOLEAN DEFAULT FALSE,
    override_reason TEXT,
    override_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
""")

# 4. Duty Log
cur.execute("""
CREATE TABLE IF NOT EXISTS duty_log (
    id SERIAL PRIMARY KEY,
    crew_id INTEGER REFERENCES crew_master(id),
    duty_start TIMESTAMP NOT NULL,
    duty_end TIMESTAMP NOT NULL,
    flight_id INTEGER REFERENCES flight_schedule(id),
    total_duty_hours NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);
""")

# 5. Legality Violations
cur.execute("""
CREATE TABLE IF NOT EXISTS legality_violations (
    id SERIAL PRIMARY KEY,
    crew_id INTEGER REFERENCES crew_master(id),
    flight_id INTEGER REFERENCES flight_schedule(id),
    violation_type VARCHAR(100),
    details TEXT,
    flagged_at TIMESTAMP DEFAULT NOW()
);
""")

# 6. Audit Trail
cur.execute("""
CREATE TABLE IF NOT EXISTS audit_trail (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    performed_by VARCHAR(100),
    target_table VARCHAR(50),
    target_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);
""")

# 7. Notification Log
cur.execute("""
CREATE TABLE IF NOT EXISTS notification_log (
    id SERIAL PRIMARY KEY,
    crew_id INTEGER REFERENCES crew_master(id),
    message_text TEXT,
    whatsapp_message_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'sent',
    sent_at TIMESTAMP DEFAULT NOW()
);
""")

conn.commit()
cur.close()
conn.close()

print("✅ All tables created successfully!")