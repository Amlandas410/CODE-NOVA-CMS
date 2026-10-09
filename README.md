# CODE-NOVA CMS Campus OS — Full Multi-Role Demo

CODE-NOVA CMS is a low-bandwidth campus operations platform built with **HTML, CSS, JavaScript, Python Flask and MySQL**.

This package now contains the complete Phase-1/Phase-2/Phase-3 demo in one project:

- Student Portal
- Admin Control Center
- Faculty / Teacher Operations
- Hostel Warden Operations
- Shared MySQL data model and role-based login
- Expanded demo dataset for realistic hackathon testing

## Stack

- Python 3.11+ / 3.12 / 3.13
- Flask 3.1
- MySQL 8.0+
- mysql-connector-python
- HTML/CSS/vanilla JavaScript
- Werkzeug password hashing

## Dataset included

The seed creates a fresh demo dataset with:

- **48 students**
- **13 faculty/service in-charges** across academic branches and service departments
- **4 hostel wardens**
- **4 hostels**: Boys Hostel A, Boys Hostel B, Boys Hostel C, Girls Hostel A
- Years **1, 2, 3 and 4** represented
- Multiple batches such as 2023-27, 2024-28, 2025-29, 2026-30
- Courses: **B.Tech, Diploma, MBA, MCA, M.Tech, BCA**
- Branches including CSE, IT, ECE, Electrical, Civil, Mechanical, AI&DS, Diploma branches, Computer Applications and Business Administration
- Service departments including **Electrical, IT Services, Civil Works, Furniture, Plumbing, Housekeeping, Security, Mess, Facilities, Network & Lab, Academic Support and Transport**
- Attendance, timetable, class updates, leave/gate requests, document requests, fees, notices, rooms/assets, complaints, mess menus/feedback, visitor passes and gate logs

## Main features

### Student

- Dashboard and profile
- Attendance visibility and subject percentages
- Weekly timetable
- Class updates
- Leave and gate-pass requests with approval routing
- Document/certificate requests
- Fee and dues view
- Notices and targeted announcements
- Complaint/maintenance ticketing
- Automatic basic service routing
- Recurring issue detection
- Room and asset records
- Mess menu and feedback/suggestion box
- Visitor pass requests
- Gate-log visibility
- English / Hindi / Odia UI
- CODE-NOVA CMS Assist common-questions chatbot

### Admin

- Campus operations overview
- Pending request queue
- Leave/gate approvals
- Document processing
- Complaint ageing and escalation
- Staff assignment and status control
- Recurring issue view
- Resolution-time analytics
- Targeted announcements by batch/branch/year/hostel
- Class updates and timetable management
- **Fees & Dues search by student name, ID, email, course or branch**
- Hostel/visitor control
- User access control

### Faculty / Teacher

- Faculty dashboard
- Branch student roster
- Attendance entry and review
- Timetable creation
- Class updates
- Leave/gate approvals routed to teacher
- Assigned/service complaint handling
- Targeted student announcements

### Hostel Warden

- Hostel dashboard
- Resident queue
- Leave/gate approvals
- Visitor-pass approvals
- Gate-log review and live OUT/IN gate scanning
- Room and asset register management
- Hostel complaint management
- Mess menu publishing
- Mess feedback review
- Hostel-specific announcements

## Setup on Windows

### 1. Create virtual environment

```bat
cd code_nova_cms
py -3 -m venv venv
venv\Scripts\activate
```

### 2. Install packages

```bat
pip install -r requirements.txt
```

### 3. Configure MySQL

Copy `.env.example` to `.env` and set your MySQL password.

Example:

```env
FLASK_SECRET_KEY=change-this-for-a-real-deployment
FLASK_DEBUG=1
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=code_nova_cms
MYSQL_USER=root
MYSQL_PASSWORD=YOUR_MYSQL_PASSWORD
```

### 4. Create tables

For a new database:

```bat
mysql -u root -p < schema.sql
```

For an earlier CODE-NOVA CMS database from the previous package, also run:

```bat
mysql -u root -p code_nova_cms < migrations\002_full_roles.sql
```

### 5. Seed the complete demo

```bat
python seed.py
```

The seed is intentionally a **demo reset**: it truncates the CODE-NOVA CMS tables before rebuilding the sample dataset.

### 6. Run

```
cd "D:\CMS\code_nova_cms - Copy"
.\venv\Scripts\python -m waitress --listen=0.0.0.0:8000 wsgi:app 
```

```bat
python run.py
```

Open:

```text
http://127.0.0.1:5000/
```

## Demo logins

### Admin

```text
admin@gmail.com
Admin@123
```

### Faculty / Teacher

```text
teacher@gmail.com
Teacher@123
```

There are 12 additional faculty accounts using the same password. Their email addresses follow `prof.*@gmail.com` / `dr.*@gmail.com` patterns.

### Hostel Warden

```text
warden@gmail.com
Warden@123
```

There are 3 additional warden accounts using the same password.

### Student

```text
student@gmail.com
Student@123
```

There are 47 additional student records (`student02@gmail.com` through `student48@gmail.com`) using the same password.

## Role boundaries

- Students can operate only their own portal data.
- Faculty can manage academic/service workflows within their branch/department scope.
- Wardens can manage operations for their assigned hostel.
- Admin has campus-wide operational control.

## Important note about demo data

This is a hackathon-ready functional demo dataset, not production institutional data. Replace the demo accounts, passwords, secret key and seed/reset strategy before deployment.


<!-- 
cd "D:\CMS\code_nova_cms - Copy"
.\venv\Scripts\python -m waitress --listen=0.0.0.0:8000 wsgi:app -->
## Offline-first deployment

CODE-NOVA CMS now includes an offline-first foundation for browsers and installable PWAs. Authenticated devices cache the pages they visit, keep POST form changes in an IndexedDB outbox while offline, and automatically replay those changes when internet connectivity returns. A visible Online/Offline/Sync status indicator is shown while the user is signed in.

Static files are revalidated with the server on normal page loads, and the service worker uses the latest server copy when online while retaining a fallback for offline use. After editing frontend files, use a normal browser refresh; a forced refresh (Ctrl+F5) should not be needed. On Windows, restart the running app after changing Python backend files.

### Local test

1. Copy `.env.example` to `.env` and set the local MySQL credentials. For plain HTTP localhost development, use `SESSION_COOKIE_SECURE=0`.
2. Start the Flask application with `python run.py`.
3. Sign in, open the pages you need, then use browser DevTools → Network → Offline.
4. Submit a supported POST form. It should show that the change was saved locally.
5. Turn the network back on. The outbox retries automatically.

### Cloud deployment

The repository contains `render.yaml` as a starting point for deploying the Flask web service. Keep the production `.env` file out of Git. Put the cloud database host, database name, username, password, TLS/CA settings, and `FLASK_SECRET_KEY` in the hosting provider's environment variables.

### Important limitation of this first offline layer

The application currently uses cached server-rendered pages as the offline read snapshot and IndexedDB as a pending-write outbox. This makes previously visited screens and offline form submissions usable without rewriting the whole CMS. A later sync phase should migrate module data into structured IndexedDB stores (attendance, requests, complaints, visitors, etc.) when deeper offline querying/editing is required.

### Render note

The included `render.yaml` expects the cloud database to be reachable over TLS and uses port 4000 by default. TiDB Cloud's Python/MySQL Connector example uses port 4000 and supports CA verification; set `MYSQL_SSL=1` and provide the CA path when the provider requires it.
