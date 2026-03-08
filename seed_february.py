import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
import os
import random

load_dotenv()

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# February 2026 flights — same schedule as March
DAILY_FLIGHTS = [
    ('XYZ301', 'KHI', 'ISB', '08:00', '11:00'),
    ('XYZ302', 'ISB', 'KHI', '11:00', '14:00'),
    ('XYZ303', 'KHI', 'ISB', '15:00', '18:00'),
    ('XYZ304', 'ISB', 'KHI', '18:00', '21:00'),
    ('XYZ401', 'KHI', 'LHE', '09:00', '10:30'),
    ('XYZ402', 'LHE', 'KHI', '12:00', '13:30'),
    ('XYZ403', 'KHI', 'LHE', '16:00', '17:30'),
    ('XYZ404', 'LHE', 'KHI', '19:00', '20:30'),
    ('XYZ501', 'KHI', 'MUX', '10:00', '11:30'),
    ('XYZ502', 'MUX', 'PEW', '11:30', '13:30'),
    ('XYZ503', 'PEW', 'MUX', '13:30', '15:30'),
    ('XYZ504', 'MUX', 'KHI', '15:30', '17:00'),
]

FEB_START = date(2026, 2, 1)
FEB_END   = date(2026, 2, 28)

def build_feb_roster():
    conn = get_connection()
    cur  = conn.cursor()

    # Get all crew
    cur.execute("SELECT id, full_name, role FROM crew_master WHERE is_active=TRUE ORDER BY role, id")
    all_crew = cur.fetchall()
    lccs = [c for c in all_crew if c[2] == 'LCC']
    ccs  = [c for c in all_crew if c[2] == 'CC']

    # Build all Feb flights
    feb_flights = []
    d = FEB_START
    while d <= FEB_END:
        for fn, orig, dest, dep_t, arr_t in DAILY_FLIGHTS:
            dep = datetime.strptime(f"{d} {dep_t}", "%Y-%m-%d %H:%M")
            arr = datetime.strptime(f"{d} {arr_t}", "%Y-%m-%d %H:%M")
            feb_flights.append((fn, orig, dest, dep, arr, d))
        d += timedelta(days=1)

    # Assign crew with rotation — track duty dates per crew
    crew_duty_dates = {c[0]: set() for c in all_crew}
    crew_hours      = {c[0]: 0.0  for c in all_crew}
    crew_consec     = {c[0]: 0    for c in all_crew}
    crew_last_date  = {c[0]: None for c in all_crew}

    roster_rows = []
    duty_rows   = []

    for fn, orig, dest, dep, arr, duty_date in feb_flights:
        flight_hours = (arr - dep).total_seconds() / 3600

        def is_legal(cid):
            # Already assigned today
            if duty_date in crew_duty_dates[cid]:
                return False
            # Max 6 consecutive days
            last = crew_last_date[cid]
            if last and last != duty_date:
                gap = (duty_date - last).days
                if gap == 1 and crew_consec[cid] >= 6:
                    return False
            # Max monthly hours
            if crew_hours[cid] + flight_hours > 100:
                return False
            return True

        def assign(cid):
            d = duty_date
            last = crew_last_date[cid]
            if last is None:
                crew_consec[cid] = 1
            elif (d - last).days == 1:
                crew_consec[cid] += 1
            elif d != last:
                crew_consec[cid] = 1
            crew_last_date[cid]  = d
            crew_duty_dates[cid].add(d)
            crew_hours[cid]     += flight_hours
            roster_rows.append((fn, duty_date, cid))
            duty_rows.append((cid, fn, dep, arr, flight_hours))

        # Pick LCC — least hours first
        lcc_sorted = sorted(lccs, key=lambda c: crew_hours[c[0]])
        assigned_lcc = None
        for c in lcc_sorted:
            if is_legal(c[0]):
                assigned_lcc = c
                break

        # Pick 3 CCs — least hours first
        cc_sorted = sorted(ccs, key=lambda c: crew_hours[c[0]])
        assigned_ccs = []
        for c in cc_sorted:
            if len(assigned_ccs) >= 3:
                break
            if is_legal(c[0]):
                assigned_ccs.append(c)

        if assigned_lcc:
            assign(assigned_lcc[0])
        for c in assigned_ccs:
            assign(c[0])

    # Insert into duty_log only (no flight_schedule or roster for Feb — just duty history)
    print(f"Inserting {len(duty_rows)} February duty records...")

    # Delete any existing Feb duty_log entries first
    cur.execute("DELETE FROM duty_log WHERE duty_start::date BETWEEN %s AND %s", (FEB_START, FEB_END))
    conn.commit()

    chunk = 50
    for j in range(0, len(duty_rows), chunk):
        batch = duty_rows[j:j+chunk]
        for cid, fn, dep, arr, hrs in batch:
            cur.execute(
                "INSERT INTO duty_log (crew_id, flight_id, duty_start, duty_end, total_duty_hours) "
                "SELECT %s, fs.id, %s, %s, %s FROM flight_schedule fs "
                "WHERE fs.flight_number=%s AND fs.departure_time::date=%s "
                "LIMIT 1",
                (cid, dep, arr, hrs, fn, dep.date())
            )
        conn.commit()

    cur.close()
    conn.close()

    # Summary
    hours_list = sorted(crew_hours.values(), reverse=True)
    print(f"✅ February 2026 duty log seeded!")
    print(f"   → {len(duty_rows)} duty records inserted")
    print(f"   → Max crew hours: {hours_list[0]:.1f}h")
    print(f"   → Min crew hours: {hours_list[-1]:.1f}h")
    print(f"   → Avg crew hours: {sum(hours_list)/len(hours_list):.1f}h")

if __name__ == "__main__":
    build_feb_roster()
