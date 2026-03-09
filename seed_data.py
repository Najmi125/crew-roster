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

crew = [
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
]

cur.executemany("""
    INSERT INTO crew_master (employee_id, full_name, role, whatsapp_number)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (employee_id) DO NOTHING
""", crew)

# XYZ callsigns
daily_flights = [
    ('XYZ301', 'KHI', 'ISB', '08:00', '11:00', 'A320'),
    ('XYZ302', 'ISB', 'KHI', '11:00', '14:00', 'A320'),
    ('XYZ303', 'KHI', 'ISB', '15:00', '18:00', 'A320'),
    ('XYZ304', 'ISB', 'KHI', '18:00', '21:00', 'A320'),
    ('XYZ401', 'KHI', 'LHE', '09:00', '10:30', 'A320'),
    ('XYZ402', 'LHE', 'KHI', '12:00', '13:30', 'A320'),
    ('XYZ403', 'KHI', 'LHE', '16:00', '17:30', 'A320'),
    ('XYZ404', 'LHE', 'KHI', '19:00', '20:30', 'A320'),
    ('XYZ501', 'KHI', 'MUX', '10:00', '11:30', 'A320'),
    ('XYZ502', 'MUX', 'PEW', '11:30', '13:30', 'A320'),
    ('XYZ503', 'PEW', 'MUX', '13:30', '15:30', 'A320'),
    ('XYZ504', 'MUX', 'KHI', '15:30', '17:00', 'A320'),
]

today = date.today()
flights_to_insert = []
for day_offset in range(30):
    flight_date = today + timedelta(days=day_offset)
    for fn, orig, dest, dep_t, arr_t, ac in daily_flights:
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
print(f"   → {len(crew)} crew members (13 LCC + 27 CC)")
print(f"   → {len(flights_to_insert)} flights (12 daily × 30 days) — XYZ callsigns")
