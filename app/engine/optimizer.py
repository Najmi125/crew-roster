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

# Flight pairings — crew must work all legs together (KHI base)
PAIRINGS = [
    ['XYZ301', 'XYZ302'],                       # KHI→ISB→KHI  08:00-14:00
    ['XYZ303', 'XYZ304'],                       # KHI→ISB→KHI  15:00-21:00
    ['XYZ401', 'XYZ402'],                       # KHI→LHE→KHI  09:00-13:30
    ['XYZ403', 'XYZ404'],                       # KHI→LHE→KHI  16:00-20:30
    ['XYZ501', 'XYZ502', 'XYZ503', 'XYZ504'],  # KHI→MUX→PEW→MUX→KHI 10:00-17:00
]

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


class CrewState:
    def __init__(self, crew_id, name):
        self.crew_id        = crew_id
        self.name           = name
        self.duty_log       = []
        self.last_duty_date = None
        self.last_day_end   = None
        self.total_sectors  = 0
        self.total_hours    = 0.0
        self.consec_days    = 0

    def flying_hours_since(self, since):
        return sum(h for s, e, h in self.duty_log if s >= since)

    def flying_hours_on_date(self, d):
        return sum(h for s, e, h in self.duty_log if s.date() == d)

    def is_legal_pairing(self, legs):
        first_dep = legs[0][1]
        last_arr  = legs[-1][2]
        duty_date = first_dep.date()
        total_fh  = sum((arr - dep).total_seconds() / 3600 for _, dep, arr in legs)

        if self.last_duty_date and self.last_duty_date != duty_date:
            rest = (first_dep - self.last_day_end).total_seconds() / 3600
            if rest < MIN_REST_HOURS:
                return False
            if (duty_date - self.last_duty_date).days == 1 and self.consec_days >= 6:
                return False

        fdp = (last_arr - first_dep).total_seconds() / 3600
        if fdp > MAX_FDP_HOURS:
            return False

        daily = self.flying_hours_on_date(duty_date)
        if daily + total_fh > MAX_DAILY_FLY_HOURS:
            return False

        if self.flying_hours_since(first_dep - timedelta(days=7)) + total_fh > MAX_WEEKLY_FLY_HOURS:
            return False

        if self.flying_hours_since(first_dep - timedelta(days=28)) + total_fh > MAX_MONTHLY_FLY_HOURS:
            return False

        return True

    def assign_pairing(self, legs):
        duty_date = legs[0][1].date()
        for _, dep, arr in legs:
            hours = (arr - dep).total_seconds() / 3600
            self.duty_log.append((dep, arr, hours))
            self.total_hours   += hours
            self.total_sectors += 1
        if self.last_duty_date is None:
            self.consec_days = 1
        elif (duty_date - self.last_duty_date).days == 1:
            self.consec_days += 1
        elif duty_date != self.last_duty_date:
            self.consec_days = 1
        self.last_duty_date = duty_date
        self.last_day_end   = legs[-1][2]


def build_roster(start_date, end_date):
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("DELETE FROM duty_log")
    cur.execute("DELETE FROM roster")
    cur.execute("DELETE FROM legality_violations")
    conn.commit()

    cur.execute("""
        SELECT id, flight_number, departure_time, arrival_time
        FROM flight_schedule
        WHERE departure_time::date BETWEEN %s AND %s
        ORDER BY departure_time
    """, (start_date, end_date))
    all_flights = cur.fetchall()

    flight_lookup = {}
    for fid, fn, dep, arr in all_flights:
        flight_lookup[(fn, dep.date())] = (fid, dep, arr)

    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='LCC' ORDER BY id")
    lcc_states = [CrewState(r[0], r[1]) for r in cur.fetchall()]
    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='CC' ORDER BY id")
    cc_states  = [CrewState(r[0], r[1]) for r in cur.fetchall()]

    try:
        cur.execute("SELECT crew_id, leave_date FROM crew_leave")
        leave_map = {}
        for cid, ld in cur.fetchall():
            leave_map.setdefault(cid, set()).add(ld)
    except:
        leave_map = {}

    roster_rows    = []
    duty_rows      = []
    violation_rows = []

    d = start_date
    all_pairings = []
    while d <= end_date:
        for pairing_fns in PAIRINGS:
            legs = []
            valid = True
            for fn in pairing_fns:
                key = (fn, d)
                if key not in flight_lookup:
                    valid = False; break
                fid, dep, arr = flight_lookup[key]
                legs.append((fid, dep, arr))
            if valid:
                all_pairings.append((d, pairing_fns, legs))
        d += timedelta(days=1)

    total = len(all_pairings)
    for i, (duty_date, pairing_fns, legs) in enumerate(all_pairings):

        def can_work(state):
            if duty_date in leave_map.get(state.crew_id, set()):
                return False
            return state.is_legal_pairing(legs)

        lcc_sorted = sorted(lcc_states, key=lambda s: s.total_hours)
        cc_sorted  = sorted(cc_states,  key=lambda s: s.total_hours)

        assigned_lcc = next((s for s in lcc_sorted if can_work(s)), None)
        assigned_ccs = []
        for s in cc_sorted:
            if len(assigned_ccs) >= 3: break
            if can_work(s): assigned_ccs.append(s)

        if not assigned_lcc:
            violation_rows.append((legs[0][0], None, 'NO_LEGAL_LCC',
                f'No legal LCC for {pairing_fns} on {duty_date}'))
        if len(assigned_ccs) < 3:
            violation_rows.append((legs[0][0], None, 'INSUFFICIENT_CC',
                f'Only {len(assigned_ccs)}/3 CC for {pairing_fns} on {duty_date}'))

        for state in ([assigned_lcc] if assigned_lcc else []) + assigned_ccs:
            state.assign_pairing(legs)
            for fid, dep, arr in legs:
                fh = (arr - dep).total_seconds() / 3600
                roster_rows.append((fid, state.crew_id, duty_date))
                duty_rows.append((state.crew_id, fid, dep, arr, fh))

        if (i + 1) % 30 == 0:
            print(f"   {i+1}/{total} pairings processed...")

    chunk = 50
    print("   Saving roster...")
    for j in range(0, len(roster_rows), chunk):
        try:
            cur.executemany(
                "INSERT INTO roster (flight_id, crew_id, duty_date, is_manual_override) "
                "VALUES (%s,%s,%s,FALSE) ON CONFLICT DO NOTHING",
                roster_rows[j:j+chunk])
            conn.commit()
        except Exception:
            conn = get_connection(); cur = conn.cursor()
            cur.executemany(
                "INSERT INTO roster (flight_id, crew_id, duty_date, is_manual_override) "
                "VALUES (%s,%s,%s,FALSE) ON CONFLICT DO NOTHING",
                roster_rows[j:j+chunk])
            conn.commit()

    print("   Saving duty log...")
    for j in range(0, len(duty_rows), chunk):
        try:
            cur.executemany(
                "INSERT INTO duty_log (crew_id, flight_id, duty_start, duty_end, total_duty_hours) "
                "VALUES (%s,%s,%s,%s,%s)",
                duty_rows[j:j+chunk])
            conn.commit()
        except Exception:
            conn = get_connection(); cur = conn.cursor()
            cur.executemany(
                "INSERT INTO duty_log (crew_id, flight_id, duty_start, duty_end, total_duty_hours) "
                "VALUES (%s,%s,%s,%s,%s)",
                duty_rows[j:j+chunk])
            conn.commit()

    if violation_rows:
        try:
            cur.executemany(
                "INSERT INTO legality_violations (flight_id, crew_id, violation_type, details) "
                "VALUES (%s,%s,%s,%s)",
                violation_rows)
            conn.commit()
        except: pass

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
