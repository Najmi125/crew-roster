import streamlit as st
from dotenv import load_dotenv
import psycopg2
import pandas as pd
from datetime import date, timedelta
import os

load_dotenv()

st.set_page_config(
    page_title="XYZ Crew Operations Platform",
    page_icon="✈️",
    layout="wide"
)

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://raw.githubusercontent.com/Najmi125/crew-roster/main/assets/cc.jpg", width=150)
st.sidebar.title("✈️ XYZ Airlines")
st.sidebar.markdown("---")

# ── CSS & Animations ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Exo+2:wght@300;400;600&family=Share+Tech+Mono&display=swap');

  /* ── Page background ── */
  .stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2e 50%, #0a1628 100%);
  }

  /* ── Hero banner ── */
  .hero {
    background: linear-gradient(135deg, #0d1b2e 0%, #1a2d4a 40%, #0f2340 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 2rem 2.5rem 1.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
  }
  .hero::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #f59e0b, #fbbf24, #f59e0b);
    animation: shimmer 3s ease-in-out infinite;
  }
  @keyframes shimmer {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  .hero-title {
    font-family: 'Orbitron', monospace;
    font-size: 1.6rem;
    font-weight: 900;
    color: #f59e0b;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
    text-shadow: 0 0 30px rgba(245,158,11,0.4);
  }
  .hero-sub {
    font-family: 'Exo 2', sans-serif;
    font-size: 0.8rem;
    color: #64a0cc;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    margin-bottom: 1.2rem;
  }
  .hero-stats {
    display: flex;
    gap: 2rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
  }
  .hero-stat {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    color: #94b8d4;
  }
  .hero-stat span {
    color: #f59e0b;
    font-weight: bold;
  }

  /* ── Airplane SVG animation ── */
  .plane-container {
    position: absolute;
    right: 2rem;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0.15;
  }
  .plane-svg {
    width: 180px;
    animation: float 4s ease-in-out infinite;
  }
  @keyframes float {
    0%, 100% { transform: translateY(0px) rotate(-5deg); }
    50% { transform: translateY(-10px) rotate(-5deg); }
  }

  /* ── Badge strip ── */
  .badge-strip {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;
  }
  .badge {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.08em;
  }
  .badge-green  { background: #052e16; color: #4ade80; border: 1px solid #166534; }
  .badge-blue   { background: #0c1a33; color: #60a5fa; border: 1px solid #1e40af; }
  .badge-amber  { background: #2d1a00; color: #fbbf24; border: 1px solid #92400e; }

  /* ── Value cards ── */
  .value-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.8rem;
    margin-bottom: 1.5rem;
  }
  .value-card {
    background: #0d1b2e;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 1rem;
    border-top: 3px solid #f59e0b;
    transition: transform 0.2s, border-color 0.2s;
  }
  .value-card:hover {
    transform: translateY(-2px);
    border-color: #fbbf24;
  }
  .value-icon { font-size: 1.4rem; margin-bottom: 0.4rem; }
  .value-title {
    font-family: 'Exo 2', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    color: #f59e0b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
  }
  .value-desc {
    font-family: 'Exo 2', sans-serif;
    font-size: 0.7rem;
    color: #6b8fa8;
    line-height: 1.4;
  }

  /* ── Section header ── */
  .section-header {
    font-family: 'Orbitron', monospace;
    font-size: 0.8rem;
    font-weight: 700;
    color: #64a0cc;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    border-bottom: 1px solid #1e3a5f;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
  }

  /* ── Qual alerts ── */
  .qual-alert {
    background: #2d1a00;
    border-left: 4px solid #f59e0b;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    margin-bottom: 0.4rem;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: #fde68a;
  }
  .qual-expired {
    background: #1f0a0a;
    border-left: 4px solid #ef4444;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    margin-bottom: 0.4rem;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: #fca5a5;
  }

  /* ── Flight expanders ── */
  .stExpander {
    background: #0d1b2e !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 6px !important;
  }

  /* ── Day subheader ── */
  h3 {
    font-family: 'Orbitron', monospace !important;
    color: #60a5fa !important;
    font-size: 0.9rem !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Hero Banner ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="plane-container">
    <svg class="plane-svg" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M180 100L20 60L50 100L20 140L180 100Z" fill="#f59e0b" opacity="0.9"/>
      <path d="M80 100L60 70L100 80L80 100Z" fill="#fbbf24"/>
      <path d="M80 100L60 130L100 120L80 100Z" fill="#fbbf24"/>
      <path d="M50 100L30 90L40 100L30 110L50 100Z" fill="#fbbf24" opacity="0.6"/>
    </svg>
  </div>
  <div class="hero-title">✈ AI-Driven Crew Operations Optimization Platform</div>
  <div class="hero-sub">Operational Control Centre · Decision Support System</div>
  <div class="hero-stats">
    <div class="hero-stat">VALIDATED ON &nbsp;<span>MODEL XYZ AIRLINE</span></div>
    <div class="hero-stat">FLEET &nbsp;<span>3 AIRCRAFT</span></div>
    <div class="hero-stat">MONTHLY FLIGHTS &nbsp;<span>360</span></div>
    <div class="hero-stat">CREW STRENGTH &nbsp;<span>75</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Badges ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="badge-strip">
  <span class="badge badge-green">● CAA PAKISTAN FDTL COMPLIANT</span>
  <span class="badge badge-blue">⚡ INTELLIGENT 30-DAY ROLLING ARCHITECTURE</span>
  <span class="badge badge-amber">⚙ FULLY CUSTOMIZABLE FOR ANY AIRLINE SCALE</span>
  <span class="badge badge-green">🔒 COMPLETE HUMAN SCHEDULING CONTROL PRESERVED</span>
</div>
""", unsafe_allow_html=True)

# ── Strategic Value Cards ─────────────────────────────────────────────────────
st.markdown("""
<div class="value-grid">
  <div class="value-card">
    <div class="value-icon">⚖️</div>
    <div class="value-title">Equitable Utilization</div>
    <div class="value-desc">Transparent crew duty metrics prevent favoritism and ensure fair workload distribution</div>
  </div>
  <div class="value-card">
    <div class="value-icon">📋</div>
    <div class="value-title">Real-Time Duty Ledger</div>
    <div class="value-desc">Live duty record per crew member with FDTL compliance tracking across all time windows</div>
  </div>
  <div class="value-card">
    <div class="value-icon">🛡️</div>
    <div class="value-title">Automated Legality</div>
    <div class="value-desc">Instant compliance enforcement with complete audit trail for every scheduling decision</div>
  </div>
  <div class="value-card">
    <div class="value-icon">📊</div>
    <div class="value-title">Workforce Intelligence</div>
    <div class="value-desc">Data-driven planning insights to optimize crew deployment and predict future gaps</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-header">◈ LIVE OPERATIONAL STATUS — TODAY & TOMORROW</div>', unsafe_allow_html=True)

# ── DB ────────────────────────────────────────────────────────────────────────
try:
    conn = get_connection()
    cur  = conn.cursor()
    today    = date.today()
    tomorrow = today + timedelta(days=1)

    # Qualification alerts
    try:
        cur.execute("""
            SELECT cm.full_name, cm.employee_id, cq.qualification_type, cq.expiry_date
            FROM crew_qualifications cq
            JOIN crew_master cm ON cm.id = cq.crew_id
            WHERE cq.expiry_date <= %s
            ORDER BY cq.expiry_date, cm.full_name
        """, (today + timedelta(days=3),))
        alerts = cur.fetchall()

        cur.execute("""
            SELECT DISTINCT crew_id FROM crew_qualifications WHERE expiry_date <= %s
        """, (today + timedelta(days=3),))
        expiring_crew_ids = {row[0] for row in cur.fetchall()}

        cur.execute("""
            SELECT crew_id, qualification_type, expiry_date
            FROM crew_qualifications WHERE expiry_date <= %s ORDER BY expiry_date
        """, (today + timedelta(days=3),))
        crew_qual_details = {}
        for crew_id, qual_type, exp in cur.fetchall():
            crew_qual_details.setdefault(crew_id, []).append(f"{qual_type} {exp.strftime('%d %b')}")

        if alerts:
            with st.expander(f"⚠️  {len(alerts)} Qualification Alert(s) — Expand to view", expanded=True):
                for name, emp_id, qual, exp in alerts:
                    days_left = (exp - today).days
                    if days_left < 0:
                        st.markdown(
                            f'<div class="qual-expired">🔴 <b>{name}</b> ({emp_id}) — '
                            f'<b>{qual}</b> EXPIRED {exp.strftime("%d %b %Y")} ({abs(days_left)}d ago)</div>',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div class="qual-alert">🟡 <b>{name}</b> ({emp_id}) — '
                            f'<b>{qual}</b> expires {exp.strftime("%d %b %Y")} (in {days_left}d)</div>',
                            unsafe_allow_html=True)
    except Exception:
        expiring_crew_ids = set()
        crew_qual_details = {}

    # Today & Tomorrow roster
    cur.execute("""
        SELECT
            fs.departure_time::date AS duty_date,
            fs.flight_number,
            fs.origin || '→' || fs.destination AS route,
            TO_CHAR(fs.departure_time, 'HH24:MI') AS dep,
            TO_CHAR(fs.arrival_time,   'HH24:MI') AS arr,
            fs.aircraft_type,
            cm.full_name,
            cm.role,
            cm.employee_id,
            cm.id AS crew_id,
            r.is_manual_override
        FROM roster r
        JOIN flight_schedule fs ON fs.id = r.flight_id
        JOIN crew_master     cm ON cm.id = r.crew_id
        WHERE fs.departure_time::date IN (%s, %s)
        ORDER BY fs.departure_time, cm.role DESC, cm.full_name
    """, (today, tomorrow))
    rows = cur.fetchall()

    cols = ['duty_date','flight_number','route','dep','arr','aircraft_type',
            'full_name','role','employee_id','crew_id','is_manual_override']
    df = pd.DataFrame(rows, columns=cols)

    if df.empty:
        st.warning("No roster data found for today or tomorrow.")
    else:
        for duty_date in [today, tomorrow]:
            label  = "TODAY" if duty_date == today else "TOMORROW"
            day_df = df[df['duty_date'] == duty_date]
            if day_df.empty:
                continue

            st.subheader(f"📅 {label} — {duty_date.strftime('%A, %d %B %Y')}")

            for flight_num in sorted(day_df['flight_number'].unique()):
                fl_rows = day_df[day_df['flight_number'] == flight_num]
                fl_info = fl_rows.iloc[0]

                with st.expander(
                    f"✈️ {flight_num}  |  {fl_info['route']}  |  "
                    f"{fl_info['dep']}→{fl_info['arr']}  |  {fl_info['aircraft_type']}"
                ):
                    for _, crew_row in fl_rows.iterrows():
                        role_icon    = "🟡" if crew_row['role'] == 'LCC' else "🔵"
                        override_tag = " ⚠️ *Manual Override*" if crew_row['is_manual_override'] else ""
                        qual_warn    = ""
                        if crew_row['crew_id'] in expiring_crew_ids:
                            details = crew_qual_details.get(crew_row['crew_id'], [])
                            qual_warn = " 🔴 *" + " | ".join(details) + "*"
                        st.markdown(
                            f"{role_icon} **{crew_row['role']}** — "
                            f"{crew_row['full_name']} ({crew_row['employee_id']})"
                            f"{override_tag}{qual_warn}"
                        )
            st.markdown("---")

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Database connection error: {e}")
