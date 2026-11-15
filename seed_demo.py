"""Create demo accounts + sample data so every role's UI can be explored.

Usage:  python seed_demo.py          (safe to re-run; it only adds what is missing)
        python seed_demo.py --remove (deletes the demo data again)
"""
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from db import get_db, initialize_db

PASSWORD = 'demo123'
ADMIN, DOCTOR, DOCTOR2, PATIENT, LAB = 'demo_admin', 'demo_doctor', 'demo_doctor2', 'demo_patient', 'demo_lab'


def remove(c):
    c.execute("DELETE FROM appointments WHERE patient_username=? OR doctor_username IN (?,?)", (PATIENT, DOCTOR, DOCTOR2))
    c.execute("DELETE FROM doctor_slots WHERE doctor_username IN (?,?)", (DOCTOR, DOCTOR2))
    c.execute("DELETE FROM medical_records WHERE username=?", (PATIENT,))
    c.execute("DELETE FROM doctor_logins WHERE username IN (?,?)", (DOCTOR, DOCTOR2))
    c.execute("DELETE FROM doctors WHERE username IN (?,?)", (DOCTOR, DOCTOR2))
    c.execute("DELETE FROM patient_logins WHERE username=?", (PATIENT,))
    c.execute("DELETE FROM patients WHERE username=?", (PATIENT,))
    c.execute("DELETE FROM labadmin_logins WHERE username=?", (LAB,))
    c.execute("DELETE FROM lab_admins WHERE username=?", (LAB,))
    c.execute("DELETE FROM admin WHERE username=?", (ADMIN,))


def seed(c):
    pw = generate_password_hash(PASSWORD)
    if not c.execute("SELECT 1 FROM admin WHERE username=?", (ADMIN,)).fetchone():
        c.execute("INSERT INTO admin (username, password) VALUES (?, ?)", (ADMIN, pw))

    for user, name, spec, gender, exp, contact in [
        (DOCTOR, 'Anita Sharma', 'Cardiology', 'female', 12, '9876543210'),
        (DOCTOR2, 'Rahul Verma', 'Neurology', 'male', 9, '9876543211'),
    ]:
        if not c.execute("SELECT 1 FROM doctors WHERE username=?", (user,)).fetchone():
            cur = c.execute("INSERT INTO doctors (username,name,specialization,gender,experience,contact,available_slots) VALUES (?,?,?,?,?,?,?)",
                            (user, name, spec, gender, exp, contact, 6))
            c.execute("INSERT INTO doctor_logins (doctor_id, username, password) VALUES (?,?,?)", (cur.lastrowid, user, pw))

    if not c.execute("SELECT 1 FROM patients WHERE username=?", (PATIENT,)).fetchone():
        cur = c.execute("INSERT INTO patients (name,age,gender,contact,username) VALUES (?,?,?,?,?)",
                        ('Priya Nair', 29, 'female', '9876500001', PATIENT))
        c.execute("INSERT INTO patient_logins (patient_id, username, password) VALUES (?,?,?)", (cur.lastrowid, PATIENT, pw))

    if not c.execute("SELECT 1 FROM lab_admins WHERE username=?", (LAB,)).fetchone():
        cur = c.execute("INSERT INTO lab_admins (name,specialization,phone,username,password) VALUES (?,?,?,?,?)",
                        ('Kiran Das', 'Radiology', '9876511111', LAB, pw))
        c.execute("INSERT INTO labadmin_logins (labadmin_id, username, password) VALUES (?,?,?)", (cur.lastrowid, LAB, pw))

    # Future slots for both doctors; two of the first doctor's are booked by the demo patient
    if not c.execute("SELECT 1 FROM doctor_slots WHERE doctor_username=?", (DOCTOR,)).fetchone():
        now = datetime.now().replace(second=0, microsecond=0)
        fmt = lambda d: d.strftime('%Y-%m-%dT%H:%M')
        offsets = [timedelta(hours=1), timedelta(days=1, hours=2), timedelta(days=2, hours=1),
                   timedelta(days=3), timedelta(days=4, hours=3)]
        ids = []
        for o in offsets:
            ids.append(c.execute("INSERT INTO doctor_slots (doctor_username, slot_datetime, is_booked) VALUES (?,?,0)",
                                 (DOCTOR, fmt(now + o))).lastrowid)
        for o in (timedelta(days=1), timedelta(days=2, hours=4)):
            c.execute("INSERT INTO doctor_slots (doctor_username, slot_datetime, is_booked) VALUES (?,?,0)", (DOCTOR2, fmt(now + o)))
        for sid in ids[:2]:
            c.execute("UPDATE doctor_slots SET is_booked=1 WHERE slot_id=?", (sid,))
            c.execute("INSERT INTO appointments (slot_id, doctor_username, patient_username, specialization) VALUES (?,?,?,?)",
                      (sid, DOCTOR, PATIENT, 'Cardiology'))

    if not c.execute("SELECT 1 FROM medical_records WHERE username=?", (PATIENT,)).fetchone():
        c.execute("INSERT INTO medical_records (username, scan_and_report, normal_report, upload_date) VALUES (?,?,?,?)",
                  (PATIENT, None, 'https://example.com/sample-blood-report.pdf', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))


if __name__ == '__main__':
    initialize_db()
    conn = get_db()
    if '--remove' in sys.argv:
        remove(conn); msg = 'Demo data removed.'
    else:
        seed(conn)
        msg = (f"Demo accounts ready (password for all: {PASSWORD}):\n"
               f"  admin    {ADMIN}\n  doctor   {DOCTOR}\n  patient  {PATIENT}\n  lab      {LAB}")
    conn.commit(); conn.close()
    print(msg)
