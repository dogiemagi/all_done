
# Medical Management System (Flask + SQLite + Cloudinary)

A full-stack **Medical Management System** built using **Flask**, **SQLite**, and **Cloudinary**, supporting role-based access for **Admin**, **Doctor**, **Patient**, and **Lab Admin** users.

This project enables secure appointment booking, medical record uploads, and hospital administration management.


## Features

### Authentication & Roles
- Secure login with password hashing
- Role-based access control:
  - Admin
  - Doctor
  - Patient
  - Lab Admin


### Doctor Module
- View active patients
- Create and delete appointment slots
- View today’s appointments
- Access patient medical records


### Patient Module
- Book doctor appointments
- Cancel appointments (with time restriction)
- View uploaded medical records
- Account status controlled by Admin


### Lab Admin Module
- Upload medical scans & reports
- Secure storage using **Cloudinary**
- View active patient medical histories


### Admin Module
- Add / view / delete doctors, patients, and lab admins
- Activate / deactivate patient accounts
- View all medical records
- Change admin password


## What's new (UI refresh)

- Brand-new design system (`static/style.css`) with **light / dark mode** (toggle in the navbar, remembered per browser) and a fully responsive layout.
- All pages share one `base.html` layout; admin pages share a sidebar layout (`admin_base.html`).
- **Admin dashboard** with live stats and a doctors-by-specialty chart, plus a working **Change Password** page.
- **Patient dashboard** now lists upcoming and past appointments, with one-click cancel (30-minute rule enforced).
- **Doctor dashboard** shows today's / upcoming appointments, open slots and the next patient.
- Live search on doctors, patients and records; specialty filter on the home page; show/hide password on login.
- Fixes: patient cancel flow (wrong role check and date format), crash on the delete-doctors page, crash on the change-password route, `view_scan` now requires login.

## Tech Stack

| Technology | Purpose |
|---------|---------|
| Python | Backend |
| Flask | Web Framework |
| SQLite | Database |
| Cloudinary | Scan & report storage |
| HTML / CSS / Jinja2 | Frontend |
| Werkzeug | Password hashing |



## Project Structure

```
all_done/
│
├── app.py # Main Flask application
├── db.py # Database connection & initialization
├── hospital.db # SQLite database
├── su.py # Supporting utilities
│
├── templates/ # HTML templates
├── static/
│ └── images/ # Static images
│
├── pycache/ # Python cache
├── LICENSE # MIT License
└── README.md # Project documentation
```


## Installation & Setup

### Clone the Repository
```bash
git clone https://github.com/dogiemagi/all_done.git
cd medical-management-system
```

### Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies
```bash
pip install flask cloudinary werkzeug
```

## Cloudinary Configuration

Update credentials in `app.py`:
```python
cloudinary.config(
    cloud_name = 'YOUR_CLOUD_NAME',
    api_key = 'YOUR_API_KEY',
    api_secret = 'YOUR_API_SECRET'
)
```


## Run the Application

```bash
python app.py
```

Open in browser:
http://127.0.0.1:5000/



## Security Features
- Password hashing
- Session-based authentication
- Role-based route protection


