import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from io import BytesIO
from db import get_db, initialize_db
from datetime import datetime, timedelta
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api
import re

cloudinary.config(
    cloud_name = 'ddwdrw1sp',
    api_key = '592695791611253',
    api_secret = '1lJ0R3sreBjzO8CrUOv3ZF8CPcM'
)
app = Flask(__name__)
app.secret_key = 'your_secret_key'

initialize_db()

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, specialization, experience,gender FROM doctors")
    doctors = cursor.fetchall()
    conn.close()
    return render_template('index.html', doctors=doctors)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        cursor = conn.cursor()

        # ✅ Check Doctor login
        cursor.execute("SELECT doctor_id, password FROM doctor_logins WHERE username = ?", (username,))
        doc = cursor.fetchone()
        if doc and check_password_hash(doc[1], password):
            session['user_id'] = doc[0]
            session['username'] = username
            session['role'] = 'doctor'
            return redirect('/doctor')

        # ✅ Check Patient login with status check
        cursor.execute("SELECT patient_id, password, status FROM patient_logins WHERE username = ?", (username,))
        pat = cursor.fetchone()
        if pat:
            if pat[2] != 'active':
                flash("❌ Your account has been deactivated. Please contact the hospital.")
                conn.close()
                return render_template('login.html')
            if check_password_hash(pat[1], password):
                session['user_id'] = pat[0]
                session['username'] = username
                session['role'] = 'patient'
                return redirect('/user')

        # ✅ Check Lab Admin login
        cursor.execute("SELECT id, username, password FROM lab_admins WHERE username = ?", (username,))
        labadmin = cursor.fetchone()
        if labadmin and check_password_hash(labadmin[2], password):
            session['user_id'] = labadmin[0]
            session['username'] = labadmin[1]
            session['role'] = 'labadmin'
            return redirect('/labadmin')

        # ✅ Check Admin login
        cursor.execute("SELECT id, password FROM admin WHERE username = ?", (username,))
        admin = cursor.fetchone()
        if admin and check_password_hash(admin[1], password):
            session['admin'] = admin[0]
            return redirect('/admin/dashboard')
        
        conn.close()
        flash("Invalid credentials.")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def fetch_grouped_records():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id as patient_id, p.name, p.age, p.gender, p.contact, p.username, p.status,  -- Added p.status
               mr.id, mr.scan_and_report, mr.normal_report, mr.upload_date
        FROM patients p
        LEFT JOIN medical_records mr ON p.username = mr.username
        ORDER BY p.id
    """)
    rows = cursor.fetchall()
    conn.close()

    patients = {}
    for row in rows:
        username = row["username"]
        if username not in patients:
            patients[username] = {
                "id": row["patient_id"],
                "name": row["name"],
                "age": row["age"],
                "gender": row["gender"],
                "contact": row["contact"],
                "username": username,
                "status": row["status"],  # Ensure status is added
                "records": []
            }

        if row["scan_and_report"] or row["normal_report"]:
            formatted_date = row["upload_date"]
            if formatted_date:
                try:
                    # Try full datetime format first
                    dt_obj = datetime.strptime(formatted_date, "%Y-%m-%d %H:%M:%S")
                    formatted_date = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                except ValueError:
                    try:
                        # Try date only
                        dt_obj = datetime.strptime(formatted_date, "%Y-%m-%d")
                        formatted_date = dt_obj.strftime("%d/%m/%Y")
                    except ValueError:
                        pass  # keep original if nothing matches

            patients[username]["records"].append({
                "id": row["id"],
                "scan_and_report": row["scan_and_report"],
                "normal_report": row["normal_report"],
                "upload_date": formatted_date
            })

    return patients



@app.route('/doctor', methods=['GET', 'POST'])
def doctor_dashboard():
    if 'role' in session and session['role'] == 'doctor':
        return render_template('doctor_dashboard.html')
    flash("Unauthorized access. Please login.")    
    return redirect('/login')
@app.route('/doctor/doctor_view_patient', methods=['GET', 'POST'])
def doctor_view_patient():
    if 'role' not in session or session['role'] != 'doctor':        
        flash("Unauthorized access. Please login.")    
        return redirect('/login')

    if request.method == 'GET':
        return redirect(url_for('doctor_dashboard'))

    username = request.form.get('username')
    if not username:
        flash("No username provided.")
        return redirect(url_for('doctor_dashboard'))

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients WHERE username = ? OR name = ?", (username, username))
    patient = cursor.fetchone()

    if not patient:
        conn.close()
        flash("Patient not found.")
        return redirect(url_for('doctor_dashboard'))

    cursor.execute("""
        SELECT username, scan_and_report, normal_report, upload_date 
        FROM medical_records 
        WHERE username = ?
    """, (patient['username'],))
    
    records_raw = cursor.fetchall()
    records = []

    for row in records_raw:
        record = dict(row)
        upload_date = record.get("upload_date")
        if upload_date:
            try:
                dt_obj = datetime.strptime(upload_date, "%Y-%m-%d %H:%M:%S")
                record["upload_date"] = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                try:
                    dt_obj = datetime.strptime(upload_date, "%Y-%m-%d")
                    record["upload_date"] = dt_obj.strftime("%d/%m/%Y")
                except ValueError:
                    pass  # leave as is
        records.append(record)

    conn.close()

    return render_template('doctor_view_patient.html', patient=patient, records=records)


@app.route('/doctor/doctor_view_medical_record')
def doctor_view_medical_record():
    if 'role' in session and session['role'] == 'doctor':
        patients = fetch_grouped_records()

        # Filter to include only active patients
        active_patients = {
            username: patient for username, patient in patients.items() if patient.get('status') == 'active'
        }

        return render_template("doctor_view_medical_record.html", patients=active_patients)
    
    flash("Unauthorized access. Please login.")
    return redirect("/login")

    
    
@app.route('/doctor/create_slot', methods=['GET', 'POST'])
def create_slot():
    doctor_username = session.get('username')  # Get the logged-in doctor's username
    conn = get_db()
    # Automatically delete past slots
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M')
    conn.execute("""
        DELETE FROM doctor_slots 
        WHERE doctor_username = ? AND slot_datetime < ?
    """, (doctor_username, current_time))
    conn.commit()

    if request.method == 'POST':
        slot_time = request.form['slot_time']
        slot_datetime = datetime.strptime(slot_time, '%Y-%m-%dT%H:%M')  # Parse the slot time from form input
        
        # Get current time + 30 minutes
        current_time_plus_30 = datetime.now() + timedelta(minutes=30)
        
        if slot_datetime <= current_time_plus_30:
            flash('The slot must be at least 30 minutes from the current time.', 'error')
            return redirect(url_for('create_slot'))  # Prevent resubmission on refresh

        # If the slot time is valid, insert into the database
        conn.execute("INSERT INTO doctor_slots (doctor_username, slot_datetime) VALUES (?, ?)",
                     (doctor_username, slot_time))
        conn.commit()
        flash('Slot created successfully', 'success')
        return redirect(url_for('create_slot'))  # Prevent resubmission on refresh

    # Fetch slots on GET (and also after redirect from POST)
    slots = conn.execute("SELECT * FROM doctor_slots WHERE doctor_username = ?", (doctor_username,)).fetchall()

    # Format the slot_datetime to a more user-friendly format
    formatted_slots = []
    for slot in slots:
        slot_datetime_obj = datetime.strptime(slot['slot_datetime'], '%Y-%m-%dT%H:%M')

        # Formatting manually, removing leading zeros for day, month, and hour
        formatted_datetime = f"{slot_datetime_obj.day}/{slot_datetime_obj.month}/{slot_datetime_obj.year} {slot_datetime_obj.strftime('%I:%M%p').lstrip('0')}"

        formatted_slots.append({
            **slot,
            'formatted_datetime': formatted_datetime
        })

    return render_template('create_slot.html', slots=formatted_slots)



@app.route('/doctor/delete_slot/<int:slot_id>', methods=['POST'])
def delete_slot(slot_id):
    doctor_username = session.get('username')
    conn = get_db()
    conn.execute("DELETE FROM doctor_slots WHERE slot_id = ? AND doctor_username = ?", (slot_id, doctor_username))
    conn.commit()
    flash('Slot deleted successfully')
    return redirect(url_for('create_slot'))

@app.route('/doctor/appointments')
def doctor_appointments():
    if session.get('role') != 'doctor':
        return redirect(url_for('login'))
    
    doctor_username = session['username']
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    rows = conn.execute('''
        SELECT a.slot_id, s.slot_datetime, p.name AS patient_name, p.username AS patient_username
        FROM appointments a
        JOIN doctor_slots s ON a.slot_id = s.slot_id
        JOIN patients p ON a.patient_username = p.username
        WHERE s.doctor_username = ? AND DATE(s.slot_datetime) = ?
    ''', (doctor_username, today)).fetchall()

    # Format datetime correctly (for ISO format like '2025-04-18T07:07')
    appointments = []
    for row in rows:
        dt_obj = datetime.strptime(row['slot_datetime'], '%Y-%m-%dT%H:%M')
        formatted_datetime = f"{dt_obj.day}/{dt_obj.month}/{dt_obj.year} {dt_obj.strftime('%I:%M%p').lstrip('0')}"
        appointments.append({
            'slot_id': row['slot_id'],
            'slot_datetime': formatted_datetime,
            'patient_name': row['patient_name'],
            'patient_username': row['patient_username']
        })

    if not appointments:
        flash("ℹ️ No appointments for today.")  

    return render_template('appointments.html', appointments=appointments)
    
@app.route('/doctor/delete_appointment/<int:slot_id>', methods=['POST'])
def delete_appointment(slot_id):
    if session.get('role') != 'doctor':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    # Step 1: Delete from appointments table
    cursor.execute('DELETE FROM appointments WHERE slot_id = ?', (slot_id,))

    # Step 2: Delete from doctor_slots table
    cursor.execute('DELETE FROM doctor_slots WHERE slot_id = ?', (slot_id,))

    conn.commit()
    conn.close()
    flash("Appointment and slot deleted successfully.", "success")

    return redirect(url_for('doctor_appointments'))



@app.route('/user')
def user_dashboard():
    if 'role' in session and session['role'] == 'patient':
        
        return render_template('user_dashboard.html')
    flash("Unauthorized access. Please login.")
    return redirect('/login')



@app.route('/user/dashboard')
def patient_dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    username = session['username']
    conn = sqlite3.connect('your_database.db')  # Replace with your actual database connection
    cursor = conn.cursor()

    cursor.execute('''
        SELECT a.slot_id, s.slot_datetime, a.doctor_username, a.specialization
        FROM appointments a
        JOIN doctor_slots s ON a.slot_id = s.slot_id
        WHERE a.patient_username = ?
    ''', (username,))

    appointments = cursor.fetchall()

    # Debugging: Print the appointments fetched
    print(f"Appointments found: {appointments}")

    formatted_appointments = []
    for appointment in appointments:
        slot_datetime_obj = datetime.strptime(appointment[1], '%Y-%m-%dT%H:%M')
        formatted_datetime = slot_datetime_obj.strftime('%-d/%-m/%Y %-I:%M%p')
        formatted_appointments.append({
            'slot_id': appointment[0],
            'formatted_datetime': formatted_datetime,
            'doctor_name': appointment[2],
            'specialization': appointment[3]
        })

    return render_template('user_dashboard.html', appointments=formatted_appointments)


@app.route('/user/book')
def book_appointment():
    # Fetch the list of doctors for the patient to choose from
    conn = get_db()
    doctors = conn.execute("SELECT * FROM doctors").fetchall()
    return render_template('select_doctor.html', doctors=doctors)




@app.route('/user/select/<doctor_username>')
def select_doctor_slots(doctor_username):
    conn = get_db()

    # Calculate the current time plus 5 minutes
    five_minutes_from_now = datetime.now() + timedelta(minutes=5)

    # Format the time to match the database format (for comparison)
    formatted_time = five_minutes_from_now.strftime('%Y-%m-%dT%H:%M')

    # Fetch available slots for the selected doctor that are greater than 5 minutes from now 
    # and on the current or future date
    slots = conn.execute("""
        SELECT * FROM doctor_slots
        WHERE doctor_username = ? AND is_booked = 0 AND slot_datetime > ?
    """, (doctor_username, formatted_time)).fetchall()
    # If no slots are available, flash a message
    if not slots:
        flash(f"No available appointments for Dr. {doctor_username} today.", 'error') 

    # Format the slot_datetime to a more user-friendly format
    formatted_slots = []
    for slot in slots:
        # Parse the datetime
        slot_datetime_obj = datetime.strptime(slot['slot_datetime'], '%Y-%m-%dT%H:%M')

        # Manual formatting for day, month, and hour to remove leading zeros
        formatted_datetime = f"{slot_datetime_obj.day}/{slot_datetime_obj.month}/{slot_datetime_obj.year} {slot_datetime_obj.strftime('%I:%M%p').lstrip('0')}"

        # Append formatted slot
        formatted_slots.append({
            **slot,
            'formatted_datetime': formatted_datetime
        })

    return render_template('book_slot.html', slots=formatted_slots, doctor_username=doctor_username)


@app.route('/user/book_slot/<int:slot_id>/<doctor_username>', methods=['GET', 'POST'])
def confirm_booking(slot_id, doctor_username):
    if 'username' not in session:
        flash("You must be logged in to book a slot.")
        return redirect(url_for('login'))

    patient_username = session['username']
    conn = get_db()

    # Fetch the doctor's specialization from the doctors table
    doctor = conn.execute("SELECT specialization FROM doctors WHERE username = ?", (doctor_username,)).fetchone()
    if doctor:
        specialization = doctor['specialization']
    else:
        flash("Doctor not found.")
        return redirect(url_for('user_dashboard'))

    # Fetch the slot details
    slot = conn.execute("SELECT * FROM doctor_slots WHERE slot_id = ?", (slot_id,)).fetchone()
    if slot and slot['is_booked'] == 0:
        # Book the slot and create the appointment
        conn.execute("UPDATE doctor_slots SET is_booked = 1 WHERE slot_id = ?", (slot_id,))
        conn.execute(
            "INSERT INTO appointments (slot_id, doctor_username, patient_username, specialization) VALUES (?, ?, ?, ?)",
            (slot_id, doctor_username, patient_username, specialization)
        )
        conn.commit()
        flash("Slot booked successfully")
    else:
        flash("This slot is already booked or unavailable.")
    
    return redirect(url_for('user_dashboard'))




@app.route('/user/cancel/<int:slot_id>')
def cancel_booking(slot_id):
    if 'role' not in session or session['role'] != 'user':
        flash("Unauthorized access. Please login.")
        return redirect('/login')

    patient_username = session['username']
    conn = get_db()
    slot = conn.execute("SELECT slot_datetime FROM doctor_slots WHERE slot_id = ?", (slot_id,)).fetchone()

    if slot:
        from datetime import datetime, timedelta
        slot_time = datetime.strptime(slot["slot_datetime"], "%Y-%m-%d %H:%M:%S")
        if slot_time - datetime.now() > timedelta(minutes=30):
            conn.execute("DELETE FROM appointments WHERE slot_id = ? AND patient_username = ?", (slot_id, patient_username))
            conn.execute("UPDATE doctor_slots SET is_booked = 0 WHERE slot_id = ?", (slot_id,))
            conn.commit()
            flash("Appointment cancelled successfully")
        else:
            flash("Cannot cancel appointment within 30 minutes of the slot time")
    else:
        flash("Invalid slot")

    return redirect(url_for('user_dashboard'))

@app.route('/user/records')
def view_user_records():
    if 'role' in session and session['role'] == 'patient':
        username = session['username']
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, scan_and_report, normal_report, upload_date 
                FROM medical_records 
                WHERE username = ?
            """, (username,))
            rows = cursor.fetchall()

            records = []
            for row in rows:
                upload_date = row[4]
                formatted_date = upload_date
                if upload_date:
                    try:
                        dt_obj = datetime.strptime(upload_date, "%Y-%m-%d %H:%M:%S")
                        formatted_date = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                    except ValueError:
                        try:
                            dt_obj = datetime.strptime(upload_date, "%Y-%m-%d")
                            formatted_date = dt_obj.strftime("%d/%m/%Y")
                        except ValueError:
                            pass  # leave original if format unknown
                
                records.append({
                    'id': row[0],
                    'username': row[1],
                    'scan_and_report': row[2],
                    'normal_report': row[3],
                    'upload_date': formatted_date
                })

        if not records:  # If no records are found
            flash("No records found for you.")
        
        return render_template('user_medical_records.html', records=records)

    flash("Unauthorized access. Please login.")    
    return redirect('/login')



@app.route('/admin')
def admin():
    if 'role' in session and session['role'] == 'admin':
        return render_template('admin_dashboard.html')
    flash("Unauthorized access. Please login.")
    return redirect('/login')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' in session:
        return render_template('admin_dashboard.html')
    flash("Unauthorized access. Please login to view.")
    return redirect('/login')

# Generate a unique username based on the patient's name
def generate_unique_username(name, cursor):
    """Generate a unique username based on name and ensure it doesn't exist."""
    base = name.lower().replace(" ", "_")
    while True:
        suffix = uuid.uuid4().hex[:4]
        username = f"{base}_{suffix}"
        cursor.execute("SELECT 1 FROM patients WHERE username = ?", (username,))
        if not cursor.fetchone():
            return username

# Route to generate a unique username suggestion
@app.route('/generate_username')
def generate_username():
    name = request.args.get('name', 'user')
    with get_db() as conn:
        cursor = conn.cursor()
        username = generate_unique_username(name, cursor)
    return {'username': username}


        

@app.route('/admin/add_doctor_form')
def add_doctor_form():
    if 'admin' in session:
        return render_template('add_doctor.html')
    flash("Unauthorized access. Please login to view.")
    return redirect('/login')

@app.route('/admin/add_patient_form')
def add_patient_form():
    if 'admin' in session:
        return render_template('add_patient.html')
    flash("Unauthorized access. Please login to view.")
    return redirect('/login')

@app.route('/admin/add_labadmin_form')
def add_labadmin_form():
    if 'admin' in session:
        return render_template('add_labadmin.html')
    flash("Unauthorized access. Please login to view.")
    return redirect('/login')



@app.route('/admin/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if 'admin' not in session:
        flash("Unauthorized access. Please login to view.")
        return redirect('/login')

    if request.method == 'POST':
        data = request.form
        try:
            with get_db() as conn:
                cursor = conn.cursor()

                # Check if username already exists in doctors table
                cursor.execute("SELECT 1 FROM doctors WHERE username = ?", (data['username'],))
                if cursor.fetchone():
                    flash("Username already exists. Please choose a different one.")
                    return render_template('add_doctor.html', form_data=data)

                # Insert doctor data
                cursor.execute("""
                    INSERT INTO doctors (username, name, gender, specialization, experience, contact, available_slots)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['username'],  # Make sure the username is inserted here
                    data['name'],
                    data['gender'],
                    data['specialization'],
                    data['experience'],
                    data['contact'],
                    data['slots']
                ))
                doctor_id = cursor.lastrowid

                # Insert login details into doctor_logins
                password_hash = generate_password_hash(data['password'])
                cursor.execute("""
                    INSERT INTO doctor_logins (doctor_id, username, password)
                    VALUES (?, ?, ?)
                """, (doctor_id, data['username'], password_hash))

                flash("✅ Doctor added successfully with username: " + data['username'])
                return redirect('/admin/add_doctor')

        except sqlite3.IntegrityError:
            flash("❌ Username already exists or invalid data.")
            return render_template('add_doctor.html', form_data=data)

    # GET method
    return render_template('add_doctor.html')

# Route to add a new patient@app.route('/admin/add_patient', methods=['GET', 'POST'])
@app.route('/admin/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'admin' not in session:
        flash("Unauthorized access. Please login to view.")
        return redirect('/login')

    if request.method == 'POST':
        try:
            # Sanitize username
            def sanitize_folder_name(name):
                return re.sub(r'[^\w\-]', '_', name)

            name = request.form['name']
            username = sanitize_folder_name(request.form['username'])

            # Function to create nested folders
            def create_nested_folders(parent_folder, subfolders):
                # Create the parent folder first
                try:
                    cloudinary.api.create_folder(parent_folder)
                    print(f"Created parent folder: {parent_folder}")
                except Exception as e:
                    print(f"Error creating parent folder: {e}")
                    return  # Stop if the parent folder cannot be created

                # Create each subfolder inside the parent folder
                for subfolder in subfolders:
                    folder_path = f"{parent_folder}/{subfolder}"
                    try:
                        cloudinary.api.create_folder(folder_path)
                        print(f"Created subfolder: {folder_path}")
                    except Exception as e:
                        print(f"Error creating subfolder {folder_path}: {e}")

            # Correctly format the parent folder with the sanitized username
            parent_folder = f"patients/{username}"  # Outer folder
            subfolders = ["Scans", "Reports"]  # Two inner folders
            create_nested_folders(parent_folder, subfolders)

            # Process form data
            data = request.form.to_dict()
            with get_db() as conn:
                cursor = conn.cursor()

                # Check if username already exists
                cursor.execute("SELECT 1 FROM patients WHERE username = ?", (data['username'],))
                if cursor.fetchone():
                    flash("Username already exists. Please try again.")
                    return render_template(
                        'add_patient.html',
                        suggested_username=data['username'],
                        form_data=data
                    )

                # Insert into patients table
                cursor.execute("""
                    INSERT INTO patients (name, age, gender, contact, username)
                    VALUES (?, ?, ?, ?, ?)
                """, (data['name'], data['age'], data['gender'], data['contact'], data['username']))
                
                patient_id = cursor.lastrowid

                # Insert into login table
                password_hash = generate_password_hash(data['password'])
                cursor.execute("""
                    INSERT INTO patient_logins (patient_id, username, password)
                    VALUES (?, ?, ?)
                """, (patient_id, data['username'], password_hash))

                flash(f"✅ Patient added successfully with username: {data['username']}")
                return redirect('/admin/add_patient')
        except sqlite3.IntegrityError:
            flash("❌ Failed to add patient. Possibly duplicate username or invalid data.")
            return render_template(
                'add_patient.html',
                suggested_username=data.get('username', ''),
                form_data=data
            )

    # GET request - generate initial suggested username
    name = request.args.get('name', 'patient')
    with get_db() as conn:
        cursor = conn.cursor()
        suggested_username = generate_unique_username(name, cursor)
    return render_template('add_patient.html', suggested_username=suggested_username)

@app.route('/admin/add_labadmin', methods=['GET', 'POST'])
def add_labadmin():
    if 'admin' not in session:
        flash("Unauthorized access. Please login to view.")
        return redirect('/login')

    if request.method == 'POST':
        data = request.form
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                hashed_password = generate_password_hash(data['password'])

                cursor.execute("""
                    INSERT INTO lab_admins (name, specialization, phone, username, password)
                    VALUES (?, ?, ?, ?, ?)
                """, (data['name'], data['specialization'], data['phone'], data['username'], hashed_password))

                labadmin_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO labadmin_logins (labadmin_id, username, password)
                    VALUES (?, ?, ?)
                """, (labadmin_id, data['username'], hashed_password))

                flash("✅ Lab Admin added successfully.")
                return redirect('/admin/add_labadmin')
        except sqlite3.IntegrityError:
            flash("❌ Username already exists or data is invalid.")
            return render_template('add_labadmin.html', form_data=data)

    return render_template('add_labadmin.html')


@app.route('/admin/view_doctors')
def view_doctors():
    if 'admin' in session:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.*, l.username FROM doctors d
            JOIN doctor_logins l ON d.id = l.doctor_id
        """)
        doctors = cursor.fetchall()
        conn.close()
        return render_template('view_doctors.html', doctors=doctors)
    flash("Unauthorized access. Please login to view.")
    return redirect('/login')

@app.route('/admin/delete_doctors')
def delete_doctors():
    if 'admin' not in session:
        flash("Unauthorized access.")
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, l.username, l.password FROM doctors d
        JOIN doctor_logins l ON d.id = l.doctor_id
    """)
    doctors = cursor.fetchall()
    conn.close()
    return render_template('delete_doctors.html', doctors=doctors)

@app.route('/admin/delete_doctor/<int:doctor_id>', methods=['POST'])
def delete_doctor(doctor_id):
    if 'admin' not in session:
        flash("Unauthorized access.")
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM doctor_logins WHERE doctor_id = ?", (doctor_id,))
    cursor.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
    conn.commit()
    conn.close()

    flash("Doctor deleted successfully.")
    return redirect('/admin/delete_doctors')


@app.route('/admin/view_patients', methods=['GET'])
def view_patients():
    if 'admin' in session:
        # Get the status filter from the request args
        status = request.args.get('status', 'all')

        conn = get_db()
        cursor = conn.cursor()

        # If the status is 'all', fetch all patients
        if status == 'all':
            cursor.execute("""
                SELECT p.id, p.name, p.age, p.gender, p.contact, l.username, p.status 
                FROM patients p
                JOIN patient_logins l ON p.id = l.patient_id
                ORDER BY p.id ASC
            """)
        else:
            # Fetch patients based on the selected status (active or deactive)
            cursor.execute("""
                SELECT p.id, p.name, p.age, p.gender, p.contact, l.username, p.status 
                FROM patients p
                JOIN patient_logins l ON p.id = l.patient_id
                WHERE p.status = ?
                ORDER BY p.id ASC
            """, (status,))  # Use a tuple for parameter

        patients = cursor.fetchall()
        conn.close()

        # Pass the patients list and selected status to the template
        return render_template('view_patients.html', patients=patients, selected_status=status)

    flash("Unauthorized access. Please login to view.")
    return redirect('/login')

@app.route('/admin/deactivate_patients', methods=['GET', 'POST'])
def deactivate_patients():
    if 'admin' not in session:
        flash("Unauthorized access. Please login.")
        return redirect('/login')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            # Deactivate in patients table
            cursor.execute("UPDATE patients SET status = 'deactive' WHERE username = ?", (username,))
            # Deactivate in patient_logins table
            cursor.execute("UPDATE patient_logins SET status = 'deactive' WHERE username = ?", (username,))
            conn.commit()
            flash(f"✅ Patient '{username}' has been deactivated.")
        else:
            flash("⚠️ No patient selected.")
    
    # Show all active patients (from patients table)
    cursor.execute("SELECT * FROM patients WHERE status = 'active'")
    patients = cursor.fetchall()
    return render_template("deactivate_patients.html", patients=patients)

@app.route('/admin/activate_patients', methods=['GET', 'POST'])
def activate_patients():
    if 'admin' not in session:
        flash("Unauthorized access. Please login.")
        return redirect('/login')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            # activate in patients table
            cursor.execute("UPDATE patients SET status = 'active' WHERE username = ?", (username,))
            # activate in patient_logins table
            cursor.execute("UPDATE patient_logins SET status = 'active' WHERE username = ?", (username,))
            conn.commit()
            flash(f"✅ Patient '{username}' has been activated.")
        else:
            flash("⚠️ No patient selected.")
    
    # Show all deactivated patients
    cursor.execute("SELECT * FROM patients WHERE status = 'deactive'")
    patients = cursor.fetchall()
    return render_template("activate_patients.html", patients=patients)

@app.route('/admin/view_labadmins')
def view_labadmins():
    if 'admin' not in session:
        flash("Unauthorized access. Please login to view.")
        return redirect('/login')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.id, l.name, l.specialization, l.phone, log.username 
        FROM lab_admins l
        JOIN labadmin_logins log ON l.id = log.labadmin_id
    """)  
    labadmins = cursor.fetchall()

    return render_template('view_labadmins.html', labadmins=labadmins)


@app.route('/admin/delete_labadmins')
def delete_labadmins():
    if 'admin' not in session:
        flash("Unauthorized access.")
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, lo.username, lo.password FROM lab_admins l
        JOIN labadmin_logins lo ON l.id = lo.labadmin_id
    """)
    labadmins = cursor.fetchall()
    conn.close()
    return render_template('delete_labadmins.html', labadmins=labadmins)

@app.route('/admin/delete_labadmin/<int:labadmin_id>', methods=['POST'])
def delete_labadmin(labadmin_id):
    if 'admin' not in session:
        flash("Unauthorized access.")
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM labadmin_logins WHERE labadmin_id = ?", (labadmin_id,))
    cursor.execute("DELETE FROM lab_admins WHERE id = ?", (labadmin_id,))
    conn.commit()
    conn.close()

    flash("Lab Admin deleted successfully.")
    return redirect('/admin/delete_labadmins')



@app.route('/admin/medical-records')
def view_medical_records():
    if 'admin' in session:
        patients = fetch_grouped_records()
        return render_template("medical_records.html", patients=patients)
    flash("Unauthorized access. Please login to view.")
    return redirect('/login')




@app.route('/admin/change_password', methods=['GET','POST'])
def change_admin_password():
    if 'admin' not in session:
        flash("Unauthorized access. Please login to view.")
        return redirect('/admin/dashboard')
    
    new_password = generate_password_hash(request.form['new_password'])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE admin SET password = ? WHERE username = 'admin'", (new_password,))
    conn.commit()
    conn.close()
    flash("Password updated.")
    
    return redirect('/admin/dashboard')

@app.route('/labadmin', methods=['GET', 'POST'])
def labadmin_dashboard():
    if 'role' in session and session['role'] == 'labadmin':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM patients")
        patients = cursor.fetchall()
        conn.close()
        return render_template('labadmin_dashboard.html', patients=patients)
    flash("Unauthorized access. Please login.")
    return redirect('/login')
@app.route('/labadmin/upload', methods=['GET', 'POST'])
def upload_medical_history():
    if 'role' in session and session['role'] == 'labadmin':
        if request.method == 'POST':
            username = request.form['username']
            scan_and_report_file = request.files.get('scan_and_report')  # Corrected to access file input
            normal_report = request.form['normal_report']
            upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')                

            scan_and_report_url = None
            if scan_and_report_file:  # Check if a file was uploaded
                upload_result = cloudinary.uploader.upload(
                    scan_and_report_file,
                    folder=f"patients/{username}/Scans"
                )
                scan_and_report_url = upload_result['secure_url']

            with get_db() as conn:
                cursor = conn.cursor()

                # Check if username exists AND is active
                cursor.execute("SELECT id FROM patients WHERE username = ? AND status = 'active'", (username,))
                result = cursor.fetchone()

                if result:
                    cursor.execute("""
                        INSERT INTO medical_records (username, scan_and_report, normal_report, upload_date)
                        VALUES (?, ?, ?, ?)
                    """, (username, scan_and_report_url, normal_report, upload_date))
                    flash("✅ Medical history uploaded successfully.")
                else:
                    flash("❌ Patient username not found or patient is not active.")

            return redirect('/labadmin/upload')

        return render_template('upload_medical_history.html')
    
    flash("Unauthorized access. Please login.")
    return redirect('/login')
  
@app.route('/labadmin/view_patients')
def labadmin_view_patients():
    if 'role' in session and session['role'] == 'labadmin':
        # Fetch all patients and their records
        patients = fetch_grouped_records()
        
        # Filter to include only active patients
        active_patients = {
            username: patient for username, patient in patients.items() if patient.get('status') == 'active'
        }
        
        return render_template("labadmin_view_patients.html", patients=active_patients)
    
    flash("Unauthorized access. Please login.")
    return redirect("/login")

# filepath: d:\FINAL_MEDICAL\app.py
@app.route('/view_scan/<int:record_id>')
def view_scan(record_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT scan_and_report FROM medical_records WHERE id = ?", (record_id,))
        result = cursor.fetchone()

        # Debugging: Print the record_id and result
        print(f"Record ID: {record_id}")
        print(f"Result: {result}")

        if result and result['scan_and_report']:
            scan_and_report_url = result['scan_and_report']
            print(f"Scan and Report URL: {scan_and_report_url}")  # Debugging
            return render_template('view_scan.html', scan_and_report_url=scan_and_report_url)
        else:
            flash("❌ Scan and report not found.")
            return redirect('/labadmin')


if __name__ == '__main__':
    app.run(debug=True, threaded=False)
