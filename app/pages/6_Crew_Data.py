import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Crew Data", page_icon="👥", layout="wide")

def get_connection():
    try:
        url = st.secrets["DATABASE_URL"]
    except:
        url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Exo+2:wght@300;400;600&family=Share+Tech+Mono&display=swap');
  .page-title { font-family:'Orbitron',monospace; font-size:1.3rem; font-weight:700; color:#1a1a2e; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:0.2rem; }
  .page-sub   { font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#888; letter-spacing:0.15em; margin-bottom:1rem; }
  .alert-expired { background:#fff0f0; border-left:4px solid #dc3545; padding:0.5rem 1rem; border-radius:4px; margin-bottom:0.3rem; font-family:'Share Tech Mono',monospace; font-size:0.78rem; color:#721c24; }
  .alert-warn    { background:#fff8e1; border-left:4px solid #f59e0b; padding:0.5rem 1rem; border-radius:4px; margin-bottom:0.3rem; font-family:'Share Tech Mono',monospace; font-size:0.78rem; color:#856404; }
  .crew-table { width:100%; border-collapse:collapse; font-family:'Exo 2',sans-serif; font-size:0.78rem; }
  .crew-table th { background:#1a1a2e; color:#fff; padding:8px 10px; font-size:0.65rem; letter-spacing:0.08em; text-transform:uppercase; text-align:left; }
  .crew-table td { padding:7px 10px; border-bottom:1px solid #eee; }
  .crew-table tr:hover td { background:#f0f4ff; }
  .inactive-row td { color:#aaa; text-decoration:line-through; }
  .section-hdr { font-family:'Orbitron',monospace; font-size:0.7rem; color:#1a1a2e; letter-spacing:0.15em; border-bottom:2px solid #1a1a2e; padding-bottom:0.3rem; margin:1.2rem 0 0.8rem; text-transform:uppercase; }
  .qual-ok   { background:#e8f5e9; color:#155724; padding:1px 6px; border-radius:8px; font-size:0.65rem; }
  .qual-warn { background:#fff3cd; color:#856404; padding:1px 6px; border-radius:8px; font-size:0.65rem; }
  .qual-exp  { background:#f8d7da; color:#721c24; padding:1px 6px; border-radius:8px; font-size:0.65rem; font-weight:700; }
  .print-btn { display:inline-block; background:#1a1a2e; color:#fff; border:none; border-radius:5px; padding:6px 16px; font-size:0.75rem; cursor:pointer; font-family:'Share Tech Mono',monospace; letter-spacing:0.08em; margin-bottom:1rem; }
  @media print { .stSidebar,.stButton,button,.print-btn,.stForm { display:none !important; } }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">👥 Crew Data</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">CREW MANAGEMENT & QUALIFICATION CURRENCY — OCC UPDATE PORTAL</div>', unsafe_allow_html=True)

try:
    conn = get_connection()
    cur  = conn.cursor()
    today = date.today()

    # ── Qualification Alerts ──────────────────────────────────────────────────
    try:
        cur.execute("""
            SELECT cm.full_name, cm.employee_id, cq.qualification_type, cq.expiry_date
            FROM crew_qualifications cq
            JOIN crew_master cm ON cm.id = cq.crew_id
            WHERE cq.expiry_date <= %s
            ORDER BY cq.expiry_date
        """, (today + timedelta(days=3),))
        alerts = cur.fetchall()
        if alerts:
            with st.expander(f"⚠️ {len(alerts)} Qualification Alert(s)", expanded=True):
                for name, emp_id, qt, exp in alerts:
                    days_left = (exp - today).days
                    if days_left < 0:
                        st.markdown(f'<div class="alert-expired">🔴 {name} ({emp_id}) — {qt} EXPIRED {exp.strftime("%d %b %Y")} ({abs(days_left)}d ago)</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="alert-warn">🟡 {name} ({emp_id}) — {qt} expires {exp.strftime("%d %b %Y")} (in {days_left}d)</div>', unsafe_allow_html=True)
    except:
        pass

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📋 Crew List & Qualifications", "✏️ Update Qualifications", "➕ Add / Deactivate Crew"])

    # ── TAB 1: Crew List ──────────────────────────────────────────────────────
    with tab1:
        st.markdown('<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>', unsafe_allow_html=True)

        cur.execute("""
            SELECT cm.id, cm.employee_id, cm.full_name, cm.role, cm.whatsapp_number, cm.is_active
            FROM crew_master cm ORDER BY cm.role, cm.full_name
        """)
        crew_rows = cur.fetchall()

        try:
            cur.execute("SELECT crew_id, qualification_type, expiry_date FROM crew_qualifications ORDER BY expiry_date")
            qual_data = {}
            for crew_id, qt, exp in cur.fetchall():
                qual_data.setdefault(crew_id, {})[qt] = exp
        except:
            qual_data = {}

        qual_types = ['Medical', 'SEP', 'CRM', 'DG']

        tbl = f"""<table class="crew-table"><thead><tr>
            <th>#</th><th>Employee ID</th><th>Name</th><th>Role</th><th>WhatsApp</th>
            {''.join(f'<th>{q}</th>' for q in qual_types)}<th>Status</th>
        </tr></thead><tbody>"""

        csv_data = []
        for i, (cid, emp_id, name, role, wp, is_active) in enumerate(crew_rows, 1):
            row_class = "" if is_active else "inactive-row"
            status    = "✅ Active" if is_active else "❌ Inactive"
            qual_cells = ""
            csv_row   = {"#": i, "ID": emp_id, "Name": name, "Role": role, "WhatsApp": wp or "", "Status": "Active" if is_active else "Inactive"}

            for qt in qual_types:
                exp = qual_data.get(cid, {}).get(qt)
                if exp is None:
                    qual_cells += '<td style="color:#ccc">—</td>'
                    csv_row[qt] = "N/A"
                else:
                    days_left = (exp - today).days
                    if days_left < 0:
                        cls, label = "qual-exp", f"EXP {exp.strftime('%d %b')}"
                    elif days_left <= 30:
                        cls, label = "qual-warn", exp.strftime('%d %b %y')
                    else:
                        cls, label = "qual-ok", exp.strftime('%d %b %y')
                    qual_cells += f'<td><span class="{cls}">{label}</span></td>'
                    csv_row[qt] = str(exp)

            tbl += f'<tr class="{row_class}"><td>{i}</td><td style="font-family:\'Share Tech Mono\',monospace">{emp_id}</td><td><b>{name}</b></td><td>{"🟡 LCC" if role=="LCC" else "🔵 CC"}</td><td style="font-size:0.7rem">{wp or "—"}</td>{qual_cells}<td>{status}</td></tr>'
            csv_data.append(csv_row)

        tbl += "</tbody></table>"
        st.markdown(tbl, unsafe_allow_html=True)

        import io
        csv_buf = io.StringIO()
        pd.DataFrame(csv_data).to_csv(csv_buf, index=False)
        st.download_button("⬇️ Download CSV", csv_buf.getvalue(),
                           file_name=f"crew_data_{today}.csv", mime="text/csv")

    # ── TAB 2: Update Qualifications ──────────────────────────────────────────
    with tab2:
        st.markdown('<div class="section-hdr">Update Qualification Expiry Date</div>', unsafe_allow_html=True)

        cur.execute("SELECT id, full_name, employee_id FROM crew_master WHERE is_active=TRUE ORDER BY full_name")
        active_crew = cur.fetchall()
        crew_options = {f"{name} ({emp_id})": cid for cid, name, emp_id in active_crew}

        with st.form("update_qual_form"):
            selected_crew = st.selectbox("Select Crew Member", list(crew_options.keys()))
            qual_type     = st.selectbox("Qualification Type", ["Medical", "SEP", "CRM", "DG"])
            new_expiry    = st.date_input("New Expiry Date", value=today + timedelta(days=365))
            notes         = st.text_input("Notes (optional)", placeholder="e.g. Renewed after training course")
            submitted     = st.form_submit_button("✅ Update Qualification")

            if submitted:
                cid = crew_options[selected_crew]
                try:
                    cur.execute("""
                        INSERT INTO crew_qualifications (crew_id, qualification_type, expiry_date, last_renewed, notes)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (crew_id, qualification_type) DO UPDATE
                            SET expiry_date = EXCLUDED.expiry_date,
                                last_renewed = %s,
                                notes = EXCLUDED.notes
                    """, (cid, qual_type, new_expiry, today, notes or None, today))
                    conn.commit()
                    st.success(f"✅ {selected_crew} — {qual_type} updated to {new_expiry.strftime('%d %b %Y')}")
                except Exception as e:
                    st.error(f"Update failed: {e}")

    # ── TAB 3: Add / Deactivate Crew ──────────────────────────────────────────
    with tab3:
        col_add, col_deact = st.columns(2)

        with col_add:
            st.markdown('<div class="section-hdr">➕ Add New Crew Member</div>', unsafe_allow_html=True)
            with st.form("add_crew_form"):
                new_emp_id  = st.text_input("Employee ID", placeholder="EMP076")
                new_name    = st.text_input("Full Name", placeholder="Capt. Ali Hassan")
                new_role    = st.selectbox("Role", ["LCC", "CC"])
                new_wp      = st.text_input("WhatsApp", placeholder="+923001234576")
                add_submit  = st.form_submit_button("➕ Add Crew Member")
                if add_submit:
                    if not new_emp_id or not new_name:
                        st.error("Employee ID and Name are required.")
                    else:
                        try:
                            cur.execute("""
                                INSERT INTO crew_master (employee_id, full_name, role, whatsapp_number)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (employee_id) DO NOTHING
                            """, (new_emp_id, new_name, new_role, new_wp or None))
                            conn.commit()
                            st.success(f"✅ {new_name} added successfully!")
                        except Exception as e:
                            st.error(f"Failed: {e}")

        with col_deact:
            st.markdown('<div class="section-hdr">🚫 Deactivate / Reactivate Crew</div>', unsafe_allow_html=True)
            cur.execute("SELECT id, full_name, employee_id, is_active FROM crew_master ORDER BY full_name")
            all_crew = cur.fetchall()
            deact_options = {f"{name} ({emp_id}) — {'Active' if a else 'Inactive'}": (cid, a)
                             for cid, name, emp_id, a in all_crew}
            with st.form("deact_crew_form"):
                sel = st.selectbox("Select Crew Member", list(deact_options.keys()))
                deact_submit = st.form_submit_button("Toggle Active/Inactive Status")
                if deact_submit:
                    cid, is_active = deact_options[sel]
                    try:
                        cur.execute("UPDATE crew_master SET is_active = %s WHERE id = %s", (not is_active, cid))
                        conn.commit()
                        new_status = "Activated" if not is_active else "Deactivated"
                        st.success(f"✅ {sel.split('(')[0].strip()} — {new_status}")
                    except Exception as e:
                        st.error(f"Failed: {e}")

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Database error: {e}")
