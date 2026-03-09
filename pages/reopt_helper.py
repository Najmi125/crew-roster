"""
Embedded re-optimizer — no external imports needed.
Call: reoptimize_from(from_date, get_connection_func)
Returns: number of roster assignments created
"""
from datetime import datetime, timedelta

MAX_MONTHLY = 100.0
MIN_REST    = 12.0
MAX_CONSEC  = 6
MAX_DAILY   = 8.0


class _State:
    def __init__(self, cid, name):
        self.crew_id     = cid
        self.name        = name
        self.log         = []
        self.total_hours = 0.0
        self.last_date   = None
        self.last_end    = None
        self.consec      = 0

    def flying_hours_since(self, since):
        return sum(h for s, e, h in self.log if s >= since)

    def is_legal(self, dep, arr):
        fh = (arr - dep).total_seconds() / 3600
        dd = dep.date()
        if self.last_date and self.last_date != dd:
            rest = (dep - self.last_end).total_seconds() / 3600
            if rest < MIN_REST:
                return False
            if (dd - self.last_date).days == 1 and self.consec >= MAX_CONSEC:
                return False
        month_start = datetime(dep.year, dep.month, 1)
        if self.flying_hours_since(month_start) + fh > MAX_MONTHLY:
            return False
        daily = sum(h for s, e, h in self.log if s.date() == dd)
        if daily + fh > MAX_DAILY:
            return False
        return True

    def assign(self, dep, arr):
        fh = (arr - dep).total_seconds() / 3600
        dd = dep.date()
        self.log.append((dep, arr, fh))
        self.total_hours += fh
        if self.last_date is None:
            self.consec = 1
        elif dd != self.last_date:
            self.consec = self.consec + 1 if (dd - self.last_date).days == 1 else 1
        self.last_date = dd
        self.last_end  = arr


def reoptimize_from(from_date, conn_func):
    end_date = from_date + timedelta(days=30)
    conn = conn_func()
    cur  = conn.cursor()

    # Locked overrides
    cur.execute("""
        SELECT r.flight_id, r.crew_id FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        WHERE r.is_manual_override = TRUE AND fs.departure_time::date >= %s
    """, (from_date,))
    locked = set(cur.fetchall())

    # Delete non-override entries from from_date
    cur.execute("""
        DELETE FROM duty_log WHERE crew_id IN (
            SELECT crew_id FROM roster WHERE is_manual_override=FALSE AND duty_date >= %s
        ) AND flight_id IN (
            SELECT flight_id FROM roster WHERE is_manual_override=FALSE AND duty_date >= %s
        ) AND duty_start::date >= %s
    """, (from_date, from_date, from_date))
    cur.execute("DELETE FROM roster WHERE is_manual_override=FALSE AND duty_date >= %s", (from_date,))
    conn.commit()

    # Flights to assign
    cur.execute("""
        SELECT id, flight_number, departure_time, arrival_time
        FROM flight_schedule WHERE departure_time::date BETWEEN %s AND %s
        ORDER BY departure_time
    """, (from_date, end_date))
    flights = cur.fetchall()

    # Crew lists
    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='LCC' ORDER BY id")
    lcc_list = cur.fetchall()
    cur.execute("SELECT id, full_name FROM crew_master WHERE is_active=TRUE AND role='CC' ORDER BY id")
    cc_list = cur.fetchall()

    # Leave map
    try:
        cur.execute("SELECT crew_id, leave_date FROM crew_leave WHERE leave_date >= %s", (from_date,))
        leave_map = {}
        for cid, ld in cur.fetchall():
            leave_map.setdefault(cid, set()).add(ld)
    except:
        leave_map = {}

    def build(cid, name):
        s = _State(cid, name)
        cur.execute("""
            SELECT duty_start, duty_end, total_duty_hours FROM duty_log
            WHERE crew_id=%s AND duty_start::date < %s ORDER BY duty_start
        """, (cid, from_date))
        for dep, arr, hrs in cur.fetchall():
            s.log.append((dep, arr, float(hrs)))
            s.total_hours += float(hrs)
            s.last_date = dep.date(); s.last_end = arr
        cur.execute("""
            SELECT fs.departure_time, fs.arrival_time FROM roster r
            JOIN flight_schedule fs ON fs.id=r.flight_id
            WHERE r.crew_id=%s AND r.is_manual_override=TRUE
            AND fs.departure_time::date >= %s ORDER BY fs.departure_time
        """, (cid, from_date))
        for dep, arr in cur.fetchall():
            fh = (arr-dep).total_seconds()/3600
            s.log.append((dep, arr, fh)); s.total_hours += fh
            s.last_date = dep.date(); s.last_end = arr
        return s

    lcc_states = [build(r[0], r[1]) for r in lcc_list]
    cc_states  = [build(r[0], r[1]) for r in cc_list]

    roster_rows, duty_rows = [], []

    for fid, fn, dep, arr in flights:
        dd = dep.date()
        lcc_s = sorted(lcc_states, key=lambda s: s.total_hours)
        cc_s  = sorted(cc_states,  key=lambda s: s.total_hours)
        assigned_lcc, assigned_ccs = None, []

        for s in lcc_s:
            if (fid, s.crew_id) in locked: continue
            if dd in leave_map.get(s.crew_id, set()): continue
            if s.is_legal(dep, arr): assigned_lcc = s; break

        for s in cc_s:
            if len(assigned_ccs) >= 3: break
            if (fid, s.crew_id) in locked: continue
            if dd in leave_map.get(s.crew_id, set()): continue
            if s.is_legal(dep, arr): assigned_ccs.append(s)

        for s in ([assigned_lcc] if assigned_lcc else []) + assigned_ccs:
            s.assign(dep, arr)
            fh = (arr-dep).total_seconds()/3600
            roster_rows.append((fid, s.crew_id, dd))
            duty_rows.append((s.crew_id, fid, dep, arr, fh))

    for i in range(0, len(roster_rows), 20):
        cur.executemany(
            "INSERT INTO roster (flight_id, crew_id, duty_date, is_manual_override) "
            "VALUES (%s,%s,%s,FALSE) ON CONFLICT DO NOTHING",
            roster_rows[i:i+20])
        conn.commit()

    for i in range(0, len(duty_rows), 20):
        cur.executemany(
            "INSERT INTO duty_log (crew_id, flight_id, duty_start, duty_end, total_duty_hours) "
            "VALUES (%s,%s,%s,%s,%s)",
            duty_rows[i:i+20])
        conn.commit()

    cur.close(); conn.close()
    return len(roster_rows)
