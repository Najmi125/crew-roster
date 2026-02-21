import psycopg2
from dotenv import load_dotenv
from datetime import date, timedelta, datetime
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# Clear old data
cur.execute("DELETE FROM duty_log")
cur.execute("DELETE FROM roster")
cur.execute("DELETE FROM legality_violations")
cur.execute("DELETE FROM flight_schedule")
cur.execute("DELETE FROM crew_master")

# ── 20 LCC + 55 CC = 75 crew ──────────────────────────────────────────────
crew = [
    # LCC (20)
   # LCC (20)
    ('EMP001', 'Ahmed Khan',        'LCC', '+923001234501'),
    ('EMP002', 'Sara Malik',        'LCC', '+923001234502'),
    ('EMP003', 'Bilal Hussain',     'LCC', '+923001234503'),
    ('EMP004', 'Nadia Farooq',      'LCC', '+923001234504'),
    ('EMP005', 'Imran Butt',        'LCC', '+923001234505'),
    ('EMP006', 'Zara Qureshi',      'LCC', '+923001234506'),
    ('EMP007', 'Hassan Ali',        'LCC', '+923001234507'),
    ('EMP008', 'Mariam Javed',      'LCC', '+923001234508'),
    ('EMP009', 'Kamran Akhtar',     'LCC', '+923001234509'),
    ('EMP010', 'Sana Rehman',       'LCC', '+923001234510'),
    ('EMP011', 'Usman Tariq',       'LCC', '+923001234511'),
    ('EMP012', 'Hina Baig',         'LCC', '+923001234512'),
    ('EMP013', 'Faisal Mahmood',    'LCC', '+923001234513'),
    ('EMP014', 'Rabia Siddiqui',    'LCC', '+923001234514'),
    ('EMP015', 'Tariq Mehmood',     'LCC', '+923001234515'),
    ('EMP016', 'Ayesha Zafar',      'LCC', '+923001234516'),
    ('EMP017', 'Danish Raza',       'LCC', '+923001234517'),
    ('EMP018', 'Kashif Anwar',      'LCC', '+923001234518'),
    ('EMP019', 'Lubna Shahid',      'LCC', '+923001234519'),
    ('EMP020', 'Waseem Akram',      'LCC', '+923001234520'),


    # CC (55)
    ('EMP021', 'Fatima Rizvi',            'CC',  '+923001234521'),
    ('EMP022', 'Omar Sheikh',             'CC',  '+923001234522'),
    ('EMP023', 'Ayesha Siddiqui',         'CC',  '+923001234523'),
    ('EMP024', 'Zainab Nawaz',            'CC',  '+923001234524'),
    ('EMP025', 'Shahzad Mirza',           'CC',  '+923001234525'),
    ('EMP026', 'Amna Khalid',             'CC',  '+923001234526'),
    ('EMP027', 'Raza Haider',             'CC',  '+923001234527'),
    ('EMP028', 'Maryam Yousuf',           'CC',  '+923001234528'),
    ('EMP029', 'Ali Raza',                'CC',  '+923001234529'),
    ('EMP030', 'Sadia Iqbal',             'CC',  '+923001234530'),
    ('EMP031', 'Waqar Ahmed',             'CC',  '+923001234531'),
    ('EMP032', 'Hira Baig',               'CC',  '+923001234532'),
    ('EMP033', 'Junaid Khan',             'CC',  '+923001234533'),
    ('EMP034', 'Saima Hussain',           'CC',  '+923001234534'),
    ('EMP035', 'Adnan Malik',             'CC',  '+923001234535'),
    ('EMP036', 'Noor Fatima',             'CC',  '+923001234536'),
    ('EMP037', 'Babar Zaman',             'CC',  '+923001234537'),
    ('EMP038', 'Iqra Saleem',             'CC',  '+923001234538'),
    ('EMP039', 'Salman Ghani',            'CC',  '+923001234539'),
    ('EMP040', 'Kiran Anwar',             'CC',  '+923001234540'),
    ('EMP041', 'Naveed Rashid',           'CC',  '+923001234541'),
    ('EMP042', 'Maira Farhan',            'CC',  '+923001234542'),
    ('EMP043', 'Hamza Shahid',            'CC',  '+923001234543'),
    ('EMP044', 'Saba Noor',               'CC',  '+923001234544'),
    ('EMP045', 'Zeeshan Awan',            'CC',  '+923001234545'),
    ('EMP046', 'Laiba Tariq',             'CC',  '+923001234546'),
    ('EMP047', 'Asad Mehmood',            'CC',  '+923001234547'),
    ('EMP048', 'Rida Kazmi',              'CC',  '+923001234548'),
    ('EMP049', 'Fawad Chaudhry',          'CC',  '+923001234549'),
    ('EMP050', 'Mehwish Anwar',           'CC',  '+923001234550'),
    ('EMP051', 'Saad Rafique',            'CC',  '+923001234551'),
    ('EMP052', 'Aroha Pervez',            'CC',  '+923001234552'),
    ('EMP053', 'Talha Asif',              'CC',  '+923001234553'),
    ('EMP054', 'Nimra Shah',              'CC',  '+923001234554'),
    ('EMP055', 'Waheed Murad',            'CC',  '+923001234555'),
    ('EMP056', 'Farah Naz',               'CC',  '+923001234556'),
    ('EMP057', 'Khalid Mahmood',          'CC',  '+923001234557'),
    ('EMP058', 'Bushra Malik',            'CC',  '+923001234558'),
    ('EMP059', 'Shoaib Akhtar',           'CC',  '+923001234559'),
    ('EMP060', 'Dur-e-Fishan',            'CC',  '+923001234560'),
    ('EMP061', 'Amir Nadeem',             'CC',  '+923001234561'),
    ('EMP062', 'Nawal Saeed',             'CC',  '+923001234562'),
    ('EMP063', 'Yasir Shah',              'CC',  '+923001234563'),
    ('EMP064', 'Ushna Shah',              'CC',  '+923001234564'),
    ('EMP065', 'Mohsin Abbas',            'CC',  '+923001234565'),
    ('EMP066', 'Yumna Zaidi',             'CC',  '+923001234566'),
    ('EMP067', 'Shehryar Munawar',        'CC',  '+923001234567'),
    ('EMP068', 'Sajal Aly',               'CC',  '+923001234568'),
    ('EMP069', 'Ahad Raza Mir',           'CC',  '+923001234569'),
    ('EMP070', 'Hania Amir',              'CC',  '+923001234570'),
    ('EMP071', 'Feroze Khan',             'CC',  '+923001234571'),
    ('EMP072', 'Zubair Hassan',           'CC',  '+923001234572'),
    ('EMP073', 'Maha Ali',                'CC',  '+923001234573'),
    ('EMP074', 'Bilal Abbas',             'CC',  '+923001234574'),
    ('EMP075', 'Sonya Hussain',           'CC',  '+923001234575'),
]

cur.executemany("""
    INSERT INTO crew_master (employee_id, full_name, role, whatsapp_number)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (employee_id) DO NOTHING
""", crew)

# ── Daily flight pattern (your exact schedule) ────────────────────────────
daily_flights = [
    # Aircraft A — KHI-ISB turnarounds
    ('PK301', 'KHI', 'ISB', '08:00', '11:00', 'A320'),
    ('PK302', 'ISB', 'KHI', '11:00', '14:00', 'A320'),
    ('PK303', 'KHI', 'ISB', '15:00', '18:00', 'A320'),
    ('PK304', 'ISB', 'KHI', '18:00', '21:00', 'A320'),
    # Aircraft B — KHI-LHE turnarounds
    ('PK401', 'KHI', 'LHE', '09:00', '10:30', 'A320'),
    ('PK402', 'LHE', 'KHI', '12:00', '13:30', 'A320'),
    ('PK403', 'KHI', 'LHE', '16:00', '17:30', 'A320'),
    ('PK404', 'LHE', 'KHI', '19:00', '20:30', 'A320'),
    # Aircraft C — KHI-MUX-PEW rotation
    ('PK501', 'KHI', 'MUX', '10:00', '11:30', 'ATR'),
    ('PK502', 'MUX', 'PEW', '11:30', '13:30', 'ATR'),
    ('PK503', 'PEW', 'MUX', '13:30', '15:30', 'ATR'),
    ('PK504', 'MUX', 'KHI', '15:30', '17:00', 'ATR'),
]

# Generate 30 days
today = date.today()
flights_to_insert = []

for day_offset in range(30):
    flight_date = today + timedelta(days=day_offset)
    for flight in daily_flights:
        fn, orig, dest, dep_t, arr_t, ac = flight
        dep = datetime.strptime(f"{flight_date} {dep_t}", "%Y-%m-%d %H:%M")
        arr = datetime.strptime(f"{flight_date} {arr_t}", "%Y-%m-%d %H:%M")
        flights_to_insert.append((fn, orig, dest, dep, arr, ac))

cur.executemany("""
    INSERT INTO flight_schedule
        (flight_number, origin, destination, departure_time, arrival_time, aircraft_type)
    VALUES (%s, %s, %s, %s, %s, %s)
""", flights_to_insert)

conn.commit()
cur.close()
conn.close()

print(f"✅ Database seeded successfully!")
print(f"   → {len(crew)} crew members (20 LCC + 55 CC)")
print(f"   → {len(flights_to_insert)} flights (12 daily × 30 days)")