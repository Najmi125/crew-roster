import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
import os

load_dotenv()

# ── CAA Pakistan FDTL Limits ──────────────────────────────────────────────
MAX_FDP_HOURS         = 13
MAX_DAILY_FLY_HOURS   = 8
MIN_REST_HOURS        = 12
MAX_WEEKLY_FLY_HOURS  = 40
MAX_MONTHLY_FLY_HOURS = 100

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

class CrewState:
    """Tracks each crew member duty state IN MEMORY — zero DB calls during optimization"""
    def __init__(self, crew_id):
        self.crew_id       = crew_id
        self.duty_log      = []
        self.last_duty_end = None

    def flying_hours_since(self, since):
        return sum(h for s, e, h in self.duty_log if s >= since)

    def is_legal(self, dep, arr):
        flight_hours = (arr - dep).total_seconds() / 3600

        # 1. Min rest
        if self.last_duty_end:
            rest = (dep - self.last_duty_end).total_seconds() / 3600
            if rest < MIN_REST_HOURS:
                return False, f"Rest {rest:.1f}h < {MIN_REST_HOURS}h"

        # 2. Max FDP
        today_start   = datetime.combine(dep.date(), datetime.min.time())
        duties_today  = [s for s, e, h in self.duty_log if s >= today_start]
        if duties_today:
            fdp = (arr - min(duties_today)).total_seconds() / 3600
            if fdp > MAX_FDP_HOURS:
                return False, f"FDP {fdp:.1f}h > {MAX_FDP_HOURS}h"

        # 3. Max daily flying
        daily = self.flying_hours_since(today_start)
        if daily + flight_hours > MAX_DAILY_FLY_HOURS:
            return False, f"Daily {daily+flight_hours:.1f}h > {MAX_DAILY_FLY_HOURS}h"

        # 4. Max weekly flying
        weekly = self.flying_hours_since(dep - timedelta(days=7))
        if weekly + flight_hours > MAX_WEEKLY_FLY_HOURS:
            return False, f"Weekly {weekly+flight_hours:.1f}h > {MAX_WEEKLY_FLY_HOURS}h"

        # 5. Max monthly flying
        monthly = self.flying_hours_since(dep - timedelta(days=28))
        if monthly + flight_hours > MAX_MONTHLY_FLY_HOURS:
            return False, f"Monthly {monthly+flight_hours:.1f}h > {MAX_MONTHLY_FLY_HOURS}h"

        return True, "Legal"

    def assign(self, dep, arr):
        hours = (arr - dep).total_seconds() / 3600
        self.duty_log.append((dep, arr, hours))
        self.last_duty_end = arr


def build_roster(start_date, end_date):
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, flight_number, departure_time, arrival_time
        FROM flight_schedule
        WHERE departure_time::date BETWEEN %s AND %s
        ORDER BY departure_time
    """, (start_date, end_date))
    flights = cur.fetchall()

    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='LCC' ORDER BY id")
    lcc_list = cur.fetchall()

    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='CC' ORDER BY id")
    cc_list = cur.fetchall()

    lcc_states = [CrewState(c[0]) for c in lcc_list]
    cc_states  = [CrewState(c[0]) for c in cc_list]

    roster_rows    = []
    duty_rows      = []
    violation_rows = []
    total          = len(flights)

    for i, flight in enumerate(flights):
        flight_id, flight_num, dep, arr = flight

        assigned_lcc = None
        assigned_ccs = []

        for state in lcc_states:
            legal, _ = state.is_legal(dep, arr)
            if legal:
                assigned_lcc = state
                break

        for state in cc_states:
            if len(assigned_ccs) >= 3:
                break
            legal, _ = state.is_legal(dep, arr)
            if legal:
                assigned_ccs.append(state)

        if not assigned_lcc:
            violation_rows.append((flight_id, None, 'NO_LEGAL_LCC',
                f'No legal LCC for {flight_num} at {dep}'))
        if len(assigned_ccs) < 3:
            violation_rows.append((flight_id, None, 'INSUFFICIENT_CC',
                f'Only {len(assigned_ccs)}/3 CC for {flight_num} at {dep}'))

        flight_hours = (arr - dep).total_seconds() / 3600
        for state in ([assigned_lcc] if assigned_lcc else []) + assigned_ccs:
            state.assign(dep, arr)
            roster_rows.append((flight_id, state.crew_id, dep.date()))
            duty_rows.append((state.crew_id, flight_id, dep, arr, flight_hours))

        if (i + 1) % 60 == 0:
            print(f"   {i+1}/{total} flights processed...")

    print("   Saving to database...")
    cur.executemany("INSERT INTO roster (flight_id, crew_id, duty_date) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", roster_rows)
    cur.executemany("INSERT INTO duty_log (crew_id, flight_id, duty_start, duty_end, total_duty_hours) VALUES (%s,%s,%s,%s,%s)", duty_rows)
    if violation_rows:
        cur.executemany("INSERT INTO legality_violations (flight_id, crew_id, violation_type, details) VALUES (%s,%s,%s,%s)", violation_rows)

    conn.commit()
    cur.close()
    conn.close()
    return len(roster_rows), len(violation_rows)


if __name__ == "__main__":
    start = date.today()
    end   = start + timedelta(days=30)
    print(f"Building 30-day roster: {start} → {end}")
    a, v = build_roster(start, end)
    print(f"✅ Roster complete!")
    print(f"   → {a} assignments made")
    print(f"   → {v} FDTL violations flagged")