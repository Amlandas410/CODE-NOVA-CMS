from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .auth import login_required
from .db import query, execute

bp = Blueprint('teacher', __name__, url_prefix='/teacher')


def teacher_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get('role') != 'teacher':
            flash('Faculty/Teacher access required.', 'danger')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def me():
    return query("SELECT * FROM users WHERE id=%s AND role='teacher'", (session['user_id'],), one=True)


def students_for(t):
    return query("SELECT id,name,student_id,course,branch,year,batch,hostel,room_no,active FROM users WHERE role='student' AND (branch=%s OR batch=%s) ORDER BY year,name", (t['branch'], t['batch'] or ''))


@bp.route('/')
@bp.route('/dashboard')
@teacher_required
def dashboard():
    t=me()
    students=students_for(t)
    kpis={
        'students': len(students),
        'attendance_low': query("SELECT COUNT(*) c FROM (SELECT student_id, SUM(present_days)/NULLIF(SUM(total_days),0)*100 pct FROM attendance GROUP BY student_id HAVING pct < 75) x", one=True)['c'],
        'pending_requests': query("SELECT COUNT(*) c FROM leave_requests lr JOIN users u ON u.id=lr.student_id WHERE lr.status='pending' AND u.branch=%s", (t['branch'],), one=True)['c'],
        'assigned_complaints': query("SELECT COUNT(*) c FROM complaints WHERE assigned_to=%s AND status NOT IN ('resolved','rejected')", (t['id'],), one=True)['c'],
    }
    recent_students=query("SELECT u.*,COALESCE(ROUND(SUM(a.present_days)/NULLIF(SUM(a.total_days),0)*100,1),0) attendance_pct FROM users u LEFT JOIN attendance a ON a.student_id=u.id WHERE u.role='student' AND u.branch=%s GROUP BY u.id ORDER BY attendance_pct ASC,u.name LIMIT 8", (t['branch'],))
    reqs=query("SELECT lr.*,u.name student_name,u.student_id,u.year,u.hostel FROM leave_requests lr JOIN users u ON u.id=lr.student_id WHERE lr.status='pending' AND u.branch=%s ORDER BY lr.created_at DESC LIMIT 8", (t['branch'],))
    return render_template('teacher/dashboard.html', teacher=t,kpis=kpis,students=recent_students,requests=reqs)


@bp.route('/students')
@teacher_required
def students():
    t=me(); q=request.args.get('q','').strip()
    sql="SELECT u.*,COALESCE(ROUND(SUM(a.present_days)/NULLIF(SUM(a.total_days),0)*100,1),0) attendance_pct FROM users u LEFT JOIN attendance a ON a.student_id=u.id WHERE u.role='student' AND u.branch=%s"
    params=[t['branch']]
    if q:
        sql += " AND (u.name LIKE %s OR u.student_id LIKE %s OR u.email LIKE %s OR u.batch LIKE %s)"
        params += [f'%{q}%']*4
    sql += " GROUP BY u.id ORDER BY u.year,u.name"
    return render_template('teacher/students.html', teacher=t, students=query(sql,tuple(params)), q=q)


@bp.route('/attendance', methods=['GET','POST'])
@teacher_required
def attendance():
    t=me(); branch=t['branch']
    students=query("SELECT id,name,student_id,year,batch FROM users WHERE role='student' AND branch=%s AND active=1 ORDER BY year,name", (branch,))
    subject=request.values.get('subject','').strip()
    year=int(request.values.get('year', t['year'] or 1) or 1)
    if request.method=='POST':
        subject=request.form['subject'].strip(); present=int(request.form['present_days']); total=int(request.form['total_days'])
        sid=int(request.form['student_id'])
        execute("INSERT INTO attendance(student_id,subject,present_days,total_days) VALUES(%s,%s,%s,%s) ON DUPLICATE KEY UPDATE present_days=VALUES(present_days), total_days=VALUES(total_days)", (sid,subject,present,total))
        flash('Attendance updated for the student.', 'success'); return redirect(url_for('teacher.attendance',subject=subject,year=year))
    rows=[]
    if subject:
        rows=query("SELECT u.id,u.name,u.student_id,u.year,u.batch,COALESCE(a.present_days,0) present_days,COALESCE(a.total_days,0) total_days,ROUND(COALESCE(a.present_days,0)/NULLIF(a.total_days,0)*100,1) percentage FROM users u LEFT JOIN attendance a ON a.student_id=u.id AND a.subject=%s WHERE u.role='student' AND u.branch=%s AND u.year=%s ORDER BY u.name", (subject,branch,year))
    subjects=query("SELECT DISTINCT subject FROM attendance a JOIN users u ON u.id=a.student_id WHERE u.branch=%s ORDER BY subject", (branch,))
    return render_template('teacher/attendance.html',teacher=t,students=students,rows=rows,subjects=subjects,subject=subject,year=year)


@bp.route('/timetable')
@teacher_required
def timetable():
    t=me(); rows=query("SELECT * FROM timetable WHERE branch=%s ORDER BY year,day_of_week,start_time", (t['branch'],))
    return render_template('teacher/timetable.html',teacher=t,timetable=rows)


@bp.post('/timetable')
@teacher_required
def timetable_create():
    t=me()
    execute("INSERT INTO timetable(branch,year,day_of_week,start_time,end_time,subject,room,teacher_name,section) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)", (t['branch'],int(request.form['year']),int(request.form['day_of_week']),request.form['start_time'],request.form['end_time'],request.form['subject'].strip(),request.form.get('room','').strip(),t['name'],request.form.get('section','A').strip()))
    flash('Faculty timetable entry added.', 'success'); return redirect(url_for('teacher.timetable'))


@bp.route('/class-updates', methods=['GET','POST'])
@teacher_required
def class_updates():
    t=me()
    if request.method=='POST':
        execute("INSERT INTO class_updates(title,body,update_type,target_batch,target_branch,target_year,starts_at,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (request.form['title'].strip(),request.form['body'].strip(),request.form.get('update_type','general'),request.form.get('target_batch') or None,t['branch'],int(request.form['target_year']) if request.form.get('target_year') else None,request.form.get('starts_at') or None,t['id']))
        flash('Class update published to the selected students.', 'success'); return redirect(url_for('teacher.class_updates'))
    updates=query("SELECT * FROM class_updates WHERE created_by=%s ORDER BY created_at DESC LIMIT 30", (t['id'],))
    batches=query("SELECT DISTINCT batch FROM users WHERE role='student' AND branch=%s ORDER BY batch", (t['branch'],))
    return render_template('teacher/updates.html',teacher=t,updates=updates,batches=batches)


@bp.route('/requests')
@teacher_required
def requests_page():
    t=me(); rows=query("SELECT lr.*,u.name student_name,u.student_id,u.year,u.hostel FROM leave_requests lr JOIN users u ON u.id=lr.student_id WHERE lr.approval_route='teacher' AND u.branch=%s ORDER BY (lr.status='pending') DESC,lr.created_at DESC", (t['branch'],))
    return render_template('teacher/requests.html',teacher=t,requests=rows)


@bp.post('/requests/<int:req_id>/decision')
@teacher_required
def request_decision(req_id):
    t=me(); status=request.form.get('status') if request.form.get('status') in ('approved','rejected') else 'pending'
    execute("UPDATE leave_requests lr JOIN users u ON u.id=lr.student_id SET lr.status=%s,lr.decision_note=%s,lr.decided_by=%s,lr.decided_at=NOW() WHERE lr.id=%s AND lr.approval_route='teacher' AND u.branch=%s", (status,request.form.get('decision_note','').strip(),t['id'],req_id,t['branch']))
    flash('Request decision recorded.', 'success'); return redirect(url_for('teacher.requests_page'))


@bp.route('/complaints')
@teacher_required
def complaints():
    t=me(); rows=query("SELECT c.*,u.name student_name,u.student_id,u.room_no AS current_room,DATEDIFF(COALESCE(c.resolved_at,NOW()),c.created_at) age_days FROM complaints c JOIN users u ON u.id=c.student_id WHERE c.assigned_to=%s OR (c.department=%s AND c.status NOT IN ('resolved','rejected')) ORDER BY (c.status='approved_not_resolved') DESC,age_days DESC,c.created_at DESC", (t['id'],t.get('department') or t['name']))
    return render_template('teacher/complaints.html',teacher=t,complaints=rows)


@bp.post('/complaints/<int:complaint_id>')
@teacher_required
def complaint_update(complaint_id):
    t=me(); status=request.form.get('status')
    allowed=('approved','in_progress','approved_not_resolved','rejected','resolved')
    if status not in allowed: status='in_progress'
    if status=='resolved':
        execute("UPDATE complaints SET assigned_to=%s,status='resolved',resolved_at=NOW() WHERE id=%s AND (assigned_to=%s OR department=%s)", (t['id'],complaint_id,t['id'],t.get('department') or t['name']))
    else:
        execute("UPDATE complaints SET assigned_to=%s,status=%s,resolved_at=NULL WHERE id=%s AND (assigned_to=%s OR department=%s)", (t['id'],status,complaint_id,t['id'],t.get('department') or t['name']))
    flash('Complaint status updated.', 'success'); return redirect(url_for('teacher.complaints'))


@bp.route('/notices', methods=['GET','POST'])
@teacher_required
def notices():
    t=me()
    if request.method=='POST':
        execute("INSERT INTO notices(title,body,sender_role,target_batch,target_branch,target_year,target_hostel,priority,action_label,action_url,created_by) VALUES(%s,%s,'teacher',%s,%s,%s,NULL,%s,%s,%s,%s)", (request.form['title'].strip(),request.form['body'].strip(),request.form.get('target_batch') or None,t['branch'],int(request.form['target_year']) if request.form.get('target_year') else None,request.form.get('priority','normal'),request.form.get('action_label') or None,request.form.get('action_url') or None,t['id']))
        flash('Targeted faculty notice sent.', 'success'); return redirect(url_for('teacher.notices'))
    rows=query("SELECT * FROM notices WHERE created_by=%s ORDER BY created_at DESC LIMIT 25", (t['id'],))
    batches=query("SELECT DISTINCT batch FROM users WHERE role='student' AND branch=%s ORDER BY batch", (t['branch'],))
    return render_template('teacher/notices.html',teacher=t,notices=rows,batches=batches)
