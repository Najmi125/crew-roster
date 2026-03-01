import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
import os

load_dotenv()

# ── CAA Pakistan FDTL Limits ──────────────────────────────────────────────────
MAX_FDP_HOURS         = 13
MAX_DAILY_FLY_HOURS   = 8
MIN_REST_HOURS        = 12
MAX_WEEKLY_FLY_HOURS  = 40
MAX_MONTHLY_FLY_HOURS = 100

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def get_flying_hours(cur, crew_id, since):
    cur.execute("""
        SELECT COALESCE(SUM(total_duty_hours), 0)
        FROM duty_log WHERE crew_id = %s AND duty_start >= %s
    """, (crew_id, since))
    return float(cur.fetchone()[0])

def get_last_duty_end(cur, crew_id):
    cur.execute("SELECT MAX(duty_end) FROM duty_log WHERE crew_id = %s", (crew_id,))
    return cur.fetchone()[0]

def get_duty_start_today(cur, crew_id, duty_date):
    cur.execute("""
        SELECT MIN(duty_start) FROM duty_log
        WHERE crew_id = %s AND duty_start::date = %s
    """, (crew_id, duty_date))
    return cur.fetchone()[0]

def check_legality(cur, crew_id, departure, arrival):
    flight_hours = (arrival - departure).total_seconds() / 3600
    duty_date    = departure.date()

    last_end = get_last_duty_end(cur, crew_id)
    if last_end:
        rest_gap = (departure - last_end).total_seconds() / 3600
        if rest_gap < MIN_REST_HOURS:
            return False, f"Insufficient rest: {rest_gap:.1f}h"

    first_start_today = get_duty_start_today(cur, crew_id, duty_date)
    if first_start_today:
        fdp = (arrival - first_start_today).total_seconds() / 3600
        if fdp > MAX_FDP_HOURS:
            return False, f"FDP exceeded: {fdp:.1f}h"

    daily_flown = get_flying_hours(cur, crew_id, datetime.combine(duty_date, datetime.min.time()))
    if daily_flown + flight_hours > MAX_DAILY_FLY_HOURS:
        return False, f"Daily flying exceeded"

    weekly_flown = get_flying_hours(cur, crew_id, departure - timedelta(days=7))
    if weekly_flown + flight_hours > MAX_WEEKLY_FLY_HOURS:
        return False, f"Weekly flying exceeded"

    monthly_flown = get_flying_hours(cur, crew_id, departure - timedelta(days=28))
    if monthly_flown + flight_hours > MAX_MONTHLY_FLY_HOURS:
        return False, f"Monthly flying exceeded"

    return True, "Legal"

def build_roster(start_date, end_date):
    conn = get_connection()
    cur  = conn.cursor()

    # Clear old roster and duty log
    cur.execute("DELETE FROM duty_log")
    cur.execute("DELETE FROM roster")
    cur.execute("DELETE FROM legality_violations")

    cur.execute("""
        SELECT id, flight_number, departure_time, arrival_time
        FROM flight_schedule
        WHERE departure_time::date BETWEEN %s AND %s
        ORDER BY departure_time
    """, (start_date, end_date))
    flights = cur.fetchall()

    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='LCC' ORDER BY id")
    lccs = cur.fetchall()

    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='CC' ORDER BY id")
    ccs  = cur.fetchall()

    total_assignments = 0
    total_violations  = 0

    # Rotating pointers — start position shifts after each assignment
    lcc_ptr = 0
    cc_ptr  = 0

    processed = 0
    for flight in flights:
        flight_id, flight_num, dep, arr = flight
        flight_hours = (arr - dep).total_seconds() / 3600

        assigned_lcc = None
        assigned_ccs = []
        flight_violations = []

        # Find 1 legal LCC — start from lcc_ptr, rotate through full list
        for i in range(len(lccs)):
            idx  = (lcc_ptr + i) % len(lccs)
            lcc  = lccs[idx]
            legal, reason = check_legality(cur, lcc[0], dep, arr)
            if legal:
                assigned_lcc = lcc
                lcc_ptr = (idx + 1) % len(lccs)  # next flight starts after this one
                break

        if not assigned_lcc:
            flight_violations.append((flight_id, None, 'NO_LEGAL_LCC',
                f'No legal LCC for {flight_num} at {dep}'))

        # Find 3 legal CCs — start from cc_ptr, rotate through full list
        checked = 0
        while len(assigned_ccs) < 3 and checked < len(ccs):
            idx  = (cc_ptr + checked) % len(ccs)
            cc   = ccs[idx]
            legal, reason = check_legality(cur, cc[0], dep, arr)
            if legal:
                assigned_ccs.append(cc)
                cc_ptr = (idx + 1) % len(ccs)
            checked += 1

        if len(assigned_ccs) < 3:
            flight_violations.append((flight_id, None, 'INSUFFICIENT_CC',
                f'Only {len(assigned_ccs)}/3 CC for {flight_num} at {dep}'))

        # Insert roster + duty log
        all_assigned = ([assigned_lcc] if assigned_lcc else []) + assigned_ccs
        for crew in all_assigned:
            cur.execute("""
                INSERT INTO roster (flight_id, crew_id, duty_date)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (flight_id, crew[0], dep.date()))

            cur.execute("""
                INSERT INTO duty_log (crew_id, flight_id, duty_start, duty_end, total_duty_hours)
                VALUES (%s, %s, %s, %s, %s)
            """, (crew[0], flight_id, dep, arr, flight_hours))

            total_assignments += 1

        for v in flight_violations:
            cur.execute("""
                INSERT INTO legality_violations (flight_id, crew_id, violation_type, details)
                VALUES (%s, %s, %s, %s)
            """, v)
            total_violations += 1

        processed += 1
        if processed % 60 == 0:
            print(f"   {processed}/{len(flights)} flights processed...")

    conn.commit()
    cur.close()
    conn.close()
    return total_assignments, total_violations

if __name__ == "__main__":
    start = date.today()
    end   = start + timedelta(days=29)
    print(f"Building 30-day roster: {start} → {end}")
    assignments, violations = build_roster(start, end)
    print(f"✅ Roster complete!")
    print(f"   → {assignments} assignments made")
    print(f"   → {violations} FDTL violations flagged")
