from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from .auth import login_required
from .db import query, execute, get_db
from .utils import pct

bp = Blueprint('student', __name__, url_prefix='/student')


@bp.before_request
def student_only():
    if session.get('role') != 'student':
        flash('Student access required.', 'danger')
        return redirect(url_for('auth.login'))


def refresh_aging_complaints():
    # Automatically escalate approved/in-progress issues still open after 2 days.
    execute("UPDATE complaints SET status='approved_not_resolved' WHERE status IN ('approved','in_progress') AND created_at < NOW()-INTERVAL 2 DAY AND resolved_at IS NULL")


def current_student():
    return query("SELECT * FROM users WHERE id=%s AND role='student'", (session['user_id'],), one=True)


def target_notice_sql(student):
    return ("WHERE (target_batch IS NULL OR target_batch=%s) "
            "AND (target_branch IS NULL OR target_branch=%s) "
            "AND (target_year IS NULL OR target_year=%s) "
            "AND (target_hostel IS NULL OR target_hostel=%s)")


def attendance_data(student_id):
    rows = query("SELECT subject,present_days,total_days,ROUND(present_days/NULLIF(total_days,0)*100,1) AS percentage FROM attendance WHERE student_id=%s ORDER BY subject", (student_id,))
    overall_present = sum(r['present_days'] for r in rows)
    overall_total = sum(r['total_days'] for r in rows)
    return rows, pct(overall_present, overall_total)


def room_asset_data(student):
    if not student['hostel'] or not student['room_no']:
        return []
    return query(
        "SELECT r.*, a.asset_name,a.asset_code,a.quantity,a.condition_status "
        "FROM rooms r LEFT JOIN assets a ON a.room_id=r.id "
        "WHERE r.hostel=%s AND r.room_no=%s",
        (student['hostel'], student['room_no'])
    )


@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    refresh_aging_complaints()
    s = current_student()
    attendance, overall = attendance_data(s['id'])
    notices = query(f"SELECT n.*, (nr.read_at IS NOT NULL) AS is_read, (nr.action_taken=1) AS action_taken FROM notices n LEFT JOIN notification_reads nr ON nr.notice_id=n.id AND nr.student_id=%s {target_notice_sql(s)} ORDER BY FIELD(n.priority,'urgent','important','normal'), n.created_at DESC LIMIT 6", (s['id'],s['batch'],s['branch'],s['year'],s['hostel']))
    complaints = query("SELECT * FROM complaints WHERE student_id=%s ORDER BY created_at DESC LIMIT 5", (s['id'],))
    requests = query("SELECT * FROM leave_requests WHERE student_id=%s ORDER BY created_at DESC LIMIT 5", (s['id'],))
    fee = query("SELECT *, GREATEST(total_dues-amount_paid-amount_refunded,0) AS amount_remaining FROM fee_accounts WHERE student_id=%s", (s['id'],), one=True)
    upcoming = query("SELECT * FROM timetable WHERE branch=%s AND year=%s ORDER BY day_of_week,start_time LIMIT 12", (s['branch'],s['year']))
    unread = query(f"SELECT COUNT(*) AS c FROM notices n LEFT JOIN notification_reads nr ON nr.notice_id=n.id AND nr.student_id=%s {target_notice_sql(s)} AND nr.read_at IS NULL", (s['id'],s['batch'],s['branch'],s['year'],s['hostel']), one=True)['c']
    room = room_asset_data(s)
    return render_template('student/dashboard.html', student=s, attendance=attendance, overall=overall, notices=notices, complaints=complaints, requests=requests, fee=fee, upcoming=upcoming, unread=unread, room=room, today=date.today())


@bp.route('/attendance')
@login_required
def attendance():
    s = current_student(); rows, overall = attendance_data(s['id'])
    return render_template('student/attendance.html', student=s, attendance=rows, overall=overall)


@bp.route('/timetable')
@login_required
def timetable():
    s = current_student()
    data = query("SELECT * FROM timetable WHERE branch=%s AND year=%s ORDER BY day_of_week,start_time", (s['branch'],s['year']))
    days = {1:'Monday',2:'Tuesday',3:'Wednesday',4:'Thursday',5:'Friday',6:'Saturday',7:'Sunday'}
    grouped = {i:[] for i in range(1,8)}
    for row in data: grouped[row['day_of_week']].append(row)
    return render_template('student/timetable.html', student=s, grouped=grouped, days=days)


@bp.route('/updates')
@login_required
def updates():
    s = current_student()
    data = query("SELECT * FROM class_updates WHERE (target_batch IS NULL OR target_batch=%s) AND (target_branch IS NULL OR target_branch=%s) AND (target_year IS NULL OR target_year=%s) ORDER BY COALESCE(starts_at,created_at) DESC", (s['batch'],s['branch'],s['year']))
    return render_template('student/updates.html', student=s, updates=data)


@bp.route('/notices')
@login_required
def notices():
    s = current_student()
    data = query(f"SELECT n.*, nr.read_at, nr.action_taken FROM notices n LEFT JOIN notification_reads nr ON nr.notice_id=n.id AND nr.student_id=%s {target_notice_sql(s)} ORDER BY FIELD(n.priority,'urgent','important','normal'), n.created_at DESC", (s['id'],s['batch'],s['branch'],s['year'],s['hostel']))
    return render_template('student/notices.html', student=s, notices=data)


@bp.post('/notices/<int:notice_id>/read')
@login_required
def mark_notice_read(notice_id):
    s = current_student()
    execute("INSERT INTO notification_reads(notice_id,student_id,read_at) VALUES(%s,%s,NOW()) ON DUPLICATE KEY UPDATE read_at=COALESCE(read_at,NOW())", (notice_id,s['id']))
    return jsonify({'ok': True})


@bp.post('/notices/<int:notice_id>/action')
@login_required
def mark_notice_action(notice_id):
    s = current_student()
    execute("INSERT INTO notification_reads(notice_id,student_id,read_at,action_taken) VALUES(%s,%s,NOW(),1) ON DUPLICATE KEY UPDATE read_at=COALESCE(read_at,NOW()), action_taken=1", (notice_id,s['id']))
    return jsonify({'ok': True})


@bp.route('/requests')
@login_required
def requests_home():
    s = current_student()
    leave = query("SELECT * FROM leave_requests WHERE student_id=%s ORDER BY created_at DESC", (s['id'],))
    docs = query("SELECT * FROM document_requests WHERE student_id=%s ORDER BY created_at DESC", (s['id'],))
    return render_template('student/requests.html', student=s, leave=leave, docs=docs)


@bp.post('/requests/leave')
@login_required
def create_leave():
    s = current_student()
    request_type = request.form.get('request_type','leave')
    try:
        start = datetime.fromisoformat(request.form['start_at'])
        end = datetime.fromisoformat(request.form['end_at'])
    except (KeyError, ValueError):
        flash('Enter valid start and end dates.', 'danger'); return redirect(url_for('student.requests_home'))
    if end <= start: flash('End time must be after start time.', 'danger'); return redirect(url_for('student.requests_home'))
    route = request.form.get('approval_route','warden' if s['hostel'] else 'teacher')
    execute("INSERT INTO leave_requests(student_id,request_type,reason,start_at,end_at,destination,emergency_contact,approval_route) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (s['id'],request_type,request.form['reason'].strip(),start,end,request.form.get('destination','').strip(),request.form.get('emergency_contact','').strip(),route))
    flash('Request submitted and routed for approval.', 'success')
    return redirect(url_for('student.requests_home'))


@bp.post('/requests/document')
@login_required
def create_document():
    s=current_student()
    copies=max(1,int(request.form.get('copies',1)))
    execute("INSERT INTO document_requests(student_id,document_type,purpose,copies,delivery_mode) VALUES(%s,%s,%s,%s,%s)", (s['id'],request.form['document_type'].strip(),request.form['purpose'].strip(),copies,request.form.get('delivery_mode','digital')))
    flash('Document request submitted to administration.', 'success')
    return redirect(url_for('student.requests_home'))


@bp.route('/fees')
@login_required
def fees():
    s=current_student(); fee=query("SELECT *, GREATEST(total_dues-amount_paid-amount_refunded,0) AS amount_remaining FROM fee_accounts WHERE student_id=%s", (s['id'],), one=True)
    return render_template('student/fees.html', student=s, fee=fee)


@bp.route('/complaints')
@login_required
def complaints():
    refresh_aging_complaints()
    s=current_student(); rows=query("SELECT * FROM complaints WHERE student_id=%s ORDER BY created_at DESC", (s['id'],))
    return render_template('student/complaints.html', student=s, complaints=rows)


@bp.post('/complaints')
@login_required
def create_complaint():
    s=current_student(); category=request.form['category']; title=request.form['title'].strip(); details=request.form['details'].strip(); room=request.form.get('room_no',s['room_no']).strip(); started=max(0,int(request.form.get('started_days',0)))
    routing = {'electrical':'Electrical','plumbing':'Plumbing','civil':'Civil Works','internet':'IT Services','cleaning':'Housekeeping','furniture':'Furniture','mess':'Mess','security':'Security','other':'Facilities'}
    dept=routing.get(category,'Facilities')
    # Basic intelligence: repeated recent category+room gets higher urgency/automatic recurring label.
    recent=query("SELECT COUNT(*) c FROM complaints WHERE student_id=%s AND category=%s AND room_no=%s AND created_at >= NOW()-INTERVAL 30 DAY", (s['id'],category,room), one=True)['c']
    if recent >= 2: details = details + "\n\n[Recurring issue detected by CODE-NOVA CMS.]"
    ticket=f"FBX-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M%S')}-{s['id']}"
    execute("INSERT INTO complaints(ticket_no,student_id,category,title,details,room_no,started_days,department,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'submitted')", (ticket,s['id'],category,title,details,room,started,dept))
    flash(f'Complaint submitted. Ticket {ticket}', 'success')
    return redirect(url_for('student.complaints'))


@bp.route('/hostel')
@login_required
def hostel():
    refresh_aging_complaints()
    s=current_student(); room=room_asset_data(s)
    return render_template('student/hostel.html', student=s, room=room)


@bp.route('/mess')
@login_required
def mess():
    s=current_student(); menu=query("SELECT * FROM mess_menu WHERE menu_date=%s ORDER BY FIELD(meal_type,'breakfast','lunch','snacks','dinner')", (date.today(),)); prev=query("SELECT * FROM mess_feedback WHERE student_id=%s ORDER BY created_at DESC LIMIT 5", (s['id'],))
    return render_template('student/mess.html', student=s, menu=menu, feedback=prev, today=date.today().isoformat())


@bp.post('/mess/feedback')
@login_required
def mess_feedback():
    s=current_student(); rating=max(1,min(5,int(request.form['rating']))); suggestion=request.form.get('suggestion','').strip()
    execute("INSERT INTO mess_feedback(student_id,menu_date,rating,suggestion) VALUES(%s,%s,%s,%s) ON DUPLICATE KEY UPDATE rating=VALUES(rating),suggestion=VALUES(suggestion)", (s['id'],date.today(),rating,suggestion))
    flash('Mess feedback recorded. Thank you.', 'success'); return redirect(url_for('student.mess'))


@bp.route('/visitors')
@login_required
def visitors():
    s=current_student(); passes=query("SELECT * FROM visitor_passes WHERE student_id=%s ORDER BY visit_date DESC,created_at DESC", (s['id'],)); logs=query("SELECT * FROM gate_logs WHERE student_id=%s ORDER BY scanned_at DESC LIMIT 20", (s['id'],))
    return render_template('student/visitors.html', student=s, passes=passes, logs=logs)


@bp.post('/visitors')
@login_required
def create_visitor():
    s=current_student(); visit_date=request.form['visit_date']
    execute("INSERT INTO visitor_passes(student_id,visitor_name,relation,phone,visit_date,purpose) VALUES(%s,%s,%s,%s,%s,%s)", (s['id'],request.form['visitor_name'].strip(),request.form.get('relation','').strip(),request.form['phone'].strip(),visit_date,request.form['purpose'].strip()))
    flash('Visitor pass request submitted to the hostel desk.', 'success'); return redirect(url_for('student.visitors'))


@bp.route('/profile')
@login_required
def profile():
    return render_template('student/profile.html', student=current_student())


@bp.post('/profile/language')
@login_required
def language():
    lang=request.form.get('language','en');
    if lang not in ('en','hi','od'): lang='en'
    execute("UPDATE users SET preferred_language=%s WHERE id=%s", (lang,session['user_id']))
    session['lang']=lang
    return redirect(request.referrer or url_for('student.dashboard'))


@bp.route('/help')
@login_required
def help_page():
    return render_template('student/help.html', student=current_student())


@bp.post('/api/chat')
@login_required
def chat():
    msg=request.get_json(silent=True) or {}; text=(msg.get('message') or '').lower()
    answers=[
        (['attendance','percentage'],'Open Attendance to see subject-wise percentage. CODE-NOVA CMS calculates it from present days divided by the attendance days entered by your teachers.'),
        (['gate pass','gatepass','permission'],'Use Requests → Leave/Gate Pass. Select the route (warden, teacher, or admin), enter duration and reason, and track the approval status.'),
        (['certificate','document'],'Use Requests → Documents & Certificates. Submit the document type, purpose, copies, and delivery mode.'),
        (['fee','dues','payment'],'Fees & Dues shows total dues, paid amount, remaining amount, and refund amount recorded for your account.'),
        (['complaint','maintenance','fan','wifi','water'],'Use Complaints & Maintenance. Pick a category, enter the room and issue duration; CODE-NOVA CMS routes it to the likely responsible department and gives you a ticket.'),
        (['mess','food','menu'],'Mess shows today’s breakfast, lunch, snacks, and dinner. You can submit a rating and suggestion.'),
        (['visitor','guest'],'Visitor & Gates lets you request a visitor pass and review gate logs.'),
    ]
    answer="I can help with Attendance, Timetable, Leave/Gate Pass, Documents, Fees, Notices, Complaints, Hostel Assets, Mess, and Visitor/Gate logs. Tell me what you need."
    for keys, value in answers:
        if any(k in text for k in keys): answer=value; break
    return jsonify({'answer':answer})
