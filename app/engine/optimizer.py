import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
import os

load_dotenv()

MAX_FDP_HOURS         = 13
MAX_DAILY_FLY_HOURS   = 8
MIN_REST_HOURS        = 12
MAX_WEEKLY_FLY_HOURS  = 40
MAX_MONTHLY_FLY_HOURS = 100

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

class CrewState:
    """Tracks crew duty entirely in memory — no DB calls during optimization"""
    def __init__(self, crew_id, name):
        self.crew_id       = crew_id
        self.name          = name
        self.duty_log      = []   # list of (dep, arr, hours)
        self.last_duty_end = None
        self.total_hours   = 0.0
        self.total_sectors = 0

    def flying_hours_since(self, since):
        return sum(h for s, e, h in self.duty_log if s >= since)

    def is_legal(self, dep, arr):
        flight_hours = (arr - dep).total_seconds() / 3600

        # Min rest since last duty
        if self.last_duty_end:
            rest = (dep - self.last_duty_end).total_seconds() / 3600
            if rest < MIN_REST_HOURS:
                return False

        # Max FDP
        today_start  = datetime.combine(dep.date(), datetime.min.time())
        duties_today = [s for s, e, h in self.duty_log if s >= today_start]
        if duties_today:
            fdp = (arr - min(duties_today)).total_seconds() / 3600
            if fdp > MAX_FDP_HOURS:
                return False

        # Max daily flying
        daily = self.flying_hours_since(today_start)
        if daily + flight_hours > MAX_DAILY_FLY_HOURS:
            return False

        # Max weekly flying
        if self.flying_hours_since(dep - timedelta(days=7)) + flight_hours > MAX_WEEKLY_FLY_HOURS:
            return False

        # Max monthly flying
        if self.flying_hours_since(dep - timedelta(days=28)) + flight_hours > MAX_MONTHLY_FLY_HOURS:
            return False

        return True

    def assign(self, dep, arr):
        hours = (arr - dep).total_seconds() / 3600
        self.duty_log.append((dep, arr, hours))
        self.last_duty_end = arr
        self.total_hours  += hours
        self.total_sectors += 1


def build_roster(start_date, end_date):
    conn = get_connection()
    cur  = conn.cursor()

    # Clear old data
    cur.execute("DELETE FROM duty_log")
    cur.execute("DELETE FROM roster")
    cur.execute("DELETE FROM legality_violations")
    conn.commit()

    # Load flights
    cur.execute("""
        SELECT id, flight_number, departure_time, arrival_time
        FROM flight_schedule
        WHERE departure_time::date BETWEEN %s AND %s
        ORDER BY departure_time
    """, (start_date, end_date))
    flights = cur.fetchall()

    # Load crew into memory
    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='LCC' ORDER BY id")
    lcc_states = [CrewState(r[0], r[1]) for r in cur.fetchall()]

    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='CC' ORDER BY id")
    cc_states = [CrewState(r[0], r[1]) for r in cur.fetchall()]

    roster_rows    = []
    duty_rows      = []
    violation_rows = []
    total          = len(flights)

    for i, (flight_id, flight_num, dep, arr) in enumerate(flights):
        flight_hours = (arr - dep).total_seconds() / 3600
        assigned_lcc = None
        assigned_ccs = []

        # Sort by least sectors assigned — ensures fair rotation
        lcc_sorted = sorted(lcc_states, key=lambda s: s.total_sectors)
        cc_sorted  = sorted(cc_states,  key=lambda s: s.total_sectors)

        # Pick first legal LCC (least used first)
        for state in lcc_sorted:
            if state.is_legal(dep, arr):
                assigned_lcc = state
                break

        # Pick 3 legal CCs (least used first)
        for state in cc_sorted:
            if len(assigned_ccs) >= 3:
                break
            if state.is_legal(dep, arr):
                assigned_ccs.append(state)

        if not assigned_lcc:
            violation_rows.append((flight_id, None, 'NO_LEGAL_LCC',
                f'No legal LCC for {flight_num} at {dep}'))
        if len(assigned_ccs) < 3:
            violation_rows.append((flight_id, None, 'INSUFFICIENT_CC',
                f'Only {len(assigned_ccs)}/3 CC for {flight_num} at {dep}'))

        # Assign and record
        for state in ([assigned_lcc] if assigned_lcc else []) + assigned_ccs:
            state.assign(dep, arr)
            roster_rows.append((flight_id, state.crew_id, dep.date()))
            duty_rows.append((state.crew_id, flight_id, dep, arr, flight_hours))

        if (i + 1) % 60 == 0:
            print(f"   {i+1}/{total} flights processed...")

    # Batch insert in chunks to avoid connection timeout
    print("   Saving roster...")
    chunk = 100
    for j in range(0, len(roster_rows), chunk):
        cur.executemany(
            "INSERT INTO roster (flight_id, crew_id, duty_date) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            roster_rows[j:j+chunk]
        )
        conn.commit()

    print("   Saving duty log...")
    for j in range(0, len(duty_rows), chunk):
        cur.executemany(
            "INSERT INTO duty_log (crew_id, flight_id, duty_start, duty_end, total_duty_hours) VALUES (%s,%s,%s,%s,%s)",
            duty_rows[j:j+chunk]
        )
        conn.commit()

    if violation_rows:
        cur.executemany(
            "INSERT INTO legality_violations (flight_id, crew_id, violation_type, details) VALUES (%s,%s,%s,%s)",
            violation_rows
        )
        conn.commit()

    cur.close()
    conn.close()
    return len(roster_rows), len(violation_rows)


if __name__ == "__main__":
    start = date.today()
    end   = start + timedelta(days=29)
    print(f"Building 30-day roster: {start} -> {end}")
    assignments, violations = build_roster(start, end)
    print(f"Roster complete!")
    print(f"   -> {assignments} assignments made")
    print(f"   -> {violations} FDTL violations flagged")
