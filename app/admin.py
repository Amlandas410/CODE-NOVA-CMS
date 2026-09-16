from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .auth import login_required
from .db import query, execute

bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Administrator access required.', 'danger')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def _user():
    return query("SELECT * FROM users WHERE id=%s", (session['user_id'],), one=True)


@bp.route('/')
@bp.route('/dashboard')
@admin_required
def dashboard():
    admin = _user()
    kpis = {
        'students': query("SELECT COUNT(*) c FROM users WHERE role='student' AND active=1", one=True)['c'],
        'pending_requests': query("SELECT COUNT(*) c FROM leave_requests WHERE status='pending'", one=True)['c'] + query("SELECT COUNT(*) c FROM document_requests WHERE status='pending'", one=True)['c'],
        'open_complaints': query("SELECT COUNT(*) c FROM complaints WHERE status NOT IN ('resolved','rejected')", one=True)['c'],
        'overdue_complaints': query("SELECT COUNT(*) c FROM complaints WHERE status NOT IN ('resolved','rejected') AND created_at < NOW()-INTERVAL 2 DAY", one=True)['c'],
        'unresolved_issues': query("SELECT COUNT(*) c FROM complaints WHERE status='approved_not_resolved'", one=True)['c'],
        'notices': query("SELECT COUNT(*) c FROM notices WHERE created_at >= NOW()-INTERVAL 30 DAY", one=True)['c'],
    }
    age_rows = query("""
        SELECT c.id,c.ticket_no,c.title,c.category,c.department,c.status,c.created_at,c.room_no,
               u.name student_name, DATEDIFF(NOW(),c.created_at) age_days
        FROM complaints c JOIN users u ON u.id=c.student_id
        WHERE c.status NOT IN ('resolved','rejected')
        ORDER BY age_days DESC, c.created_at ASC LIMIT 8
    """)
    workload = query("""
        SELECT COALESCE(u.name,'Unassigned') staff_name, COALESCE(c.department,'Unassigned') department,
               COUNT(c.id) open_count,
               SUM(c.status='approved_not_resolved') ageing_count
        FROM complaints c LEFT JOIN users u ON u.id=c.assigned_to
        WHERE c.status NOT IN ('resolved','rejected')
        GROUP BY u.id, u.name, c.department
        ORDER BY open_count DESC, ageing_count DESC LIMIT 8
    """)
    resolution = query("""
        SELECT COALESCE(ROUND(AVG(TIMESTAMPDIFF(HOUR,created_at,resolved_at)),1),0) avg_hours,
               COALESCE(MAX(TIMESTAMPDIFF(HOUR,created_at,resolved_at)),0) max_hours
        FROM complaints WHERE resolved_at IS NOT NULL
          AND created_at >= NOW()-INTERVAL 90 DAY
    """, one=True)
    repeat = query("""
        SELECT room_no, category, COUNT(*) issue_count
        FROM complaints
        WHERE created_at >= NOW()-INTERVAL 90 DAY
        GROUP BY room_no,category HAVING COUNT(*) >= 2
        ORDER BY issue_count DESC LIMIT 8
    """)
    pending = query("""
        SELECT 'Leave/Gate Pass' type, lr.id, u.name student_name, lr.reason description,
               lr.approval_route route, lr.created_at created_at, lr.status status
        FROM leave_requests lr JOIN users u ON u.id=lr.student_id WHERE lr.status='pending'
        UNION ALL
        SELECT 'Document' type, dr.id, u.name student_name, dr.document_type description,
               'admin' route, dr.created_at created_at, dr.status status
        FROM document_requests dr JOIN users u ON u.id=dr.student_id WHERE dr.status='pending'
        ORDER BY created_at DESC LIMIT 10
    """)
    return render_template('admin/dashboard.html', admin=admin, kpis=kpis, age_rows=age_rows,
                           workload=workload, resolution=resolution, repeat=repeat, pending=pending)


@bp.route('/requests')
@admin_required
def requests_page():
    admin=_user()
    leaves=query("""SELECT lr.*,u.name student_name,u.student_id,u.branch,u.year,u.hostel
                   FROM leave_requests lr JOIN users u ON u.id=lr.student_id
                   ORDER BY (lr.status='pending') DESC, lr.created_at DESC""")
    docs=query("""SELECT dr.*,u.name student_name,u.student_id,u.branch,u.year
                 FROM document_requests dr JOIN users u ON u.id=dr.student_id
                 ORDER BY (dr.status='pending') DESC, dr.created_at DESC""")
    return render_template('admin/requests.html', admin=admin, leaves=leaves, docs=docs)


@bp.post('/requests/leave/<int:req_id>/decision')
@admin_required
def leave_decision(req_id):
    status=request.form.get('status')
    if status not in ('approved','rejected'): status='pending'
    note=request.form.get('decision_note','').strip()
    if status!='pending':
        execute("UPDATE leave_requests SET status=%s,decision_note=%s,decided_by=%s,decided_at=NOW() WHERE id=%s", (status,note,session['user_id'],req_id))
        flash(f'Leave / gate request {status}.','success')
    return redirect(url_for('admin.requests_page'))


@bp.post('/requests/document/<int:req_id>/decision')
@admin_required
def document_decision(req_id):
    status=request.form.get('status')
    if status not in ('processing','ready','rejected','pending'): status='pending'
    note=request.form.get('admin_note','').strip()
    execute("UPDATE document_requests SET status=%s,admin_note=%s WHERE id=%s", (status,note,req_id))
    flash('Document request updated.','success')
    return redirect(url_for('admin.requests_page'))


@bp.route('/complaints')
@admin_required
def complaints():
    admin=_user()
    status=request.args.get('status','open')
    if status=='all':
        where="1=1"
    elif status=='closed':
        where="c.status IN ('resolved','rejected')"
    elif status=='ageing':
        where="c.status NOT IN ('resolved','rejected') AND c.created_at < NOW()-INTERVAL 2 DAY"
    else:
        where="c.status NOT IN ('resolved','rejected')"
    rows=query(f"""SELECT c.*,u.name student_name,u.student_id,u.branch,u.year,u.hostel,
                         au.name assigned_name,DATEDIFF(COALESCE(c.resolved_at,NOW()),c.created_at) age_days
                  FROM complaints c JOIN users u ON u.id=c.student_id
                  LEFT JOIN users au ON au.id=c.assigned_to
                  WHERE {where} ORDER BY (c.status='approved_not_resolved') DESC, age_days DESC, c.created_at DESC""")
    staff=query("SELECT id,name,role,branch,department,hostel FROM users WHERE active=1 AND role IN ('teacher','warden','admin') ORDER BY FIELD(role,'teacher','warden','admin'),name")
    return render_template('admin/complaints.html', admin=admin, complaints=rows, staff=staff, current_status=status)


@bp.post('/complaints/<int:complaint_id>/update')
@admin_required
def complaint_update(complaint_id):
    assigned=request.form.get('assigned_to') or None
    status=request.form.get('status')
    allowed=('submitted','approved','in_progress','approved_not_resolved','rejected','resolved')
    if status not in allowed: status='submitted'
    if status=='resolved':
        execute("UPDATE complaints SET assigned_to=%s,status=%s,resolved_at=NOW() WHERE id=%s", (assigned,status,complaint_id))
    else:
        execute("UPDATE complaints SET assigned_to=%s,status=%s,resolved_at=NULL WHERE id=%s", (assigned,status,complaint_id))
    flash('Complaint assignment/status updated.','success')
    return redirect(url_for('admin.complaints',status=request.form.get('return_status','open')))


@bp.route('/notices', methods=['GET','POST'])
@admin_required
def notices():
    admin=_user()
    if request.method=='POST':
        title=request.form.get('title','').strip(); body=request.form.get('body','').strip()
        if not title or not body:
            flash('Title and message are required.','danger')
        else:
            def val(name):
                x=request.form.get(name,'').strip()
                return x or None
            year=val('target_year')
            execute("""INSERT INTO notices(title,body,sender_role,target_batch,target_branch,target_year,target_hostel,priority,action_label,action_url,created_by)
                       VALUES(%s,%s,'admin',%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (title,body,val('target_batch'),val('target_branch'),int(year) if year else None,val('target_hostel'),
                     request.form.get('priority','normal'),val('action_label'),val('action_url'),session['user_id']))
            flash('Targeted announcement published.','success')
            return redirect(url_for('admin.notices'))
    rows=query("SELECT n.*,u.name creator, (SELECT COUNT(*) FROM notification_reads nr WHERE nr.notice_id=n.id) read_count, (SELECT COUNT(*) FROM notification_reads nr WHERE nr.notice_id=n.id AND nr.action_taken=1) action_count FROM notices n LEFT JOIN users u ON u.id=n.created_by ORDER BY n.created_at DESC LIMIT 30")
    branches=query("SELECT DISTINCT branch FROM users WHERE role='student' AND branch IS NOT NULL ORDER BY branch")
    batches=query("SELECT DISTINCT batch FROM users WHERE role='student' AND batch IS NOT NULL ORDER BY batch")
    hostels=query("SELECT DISTINCT hostel FROM users WHERE role='student' AND hostel IS NOT NULL ORDER BY hostel")
    years=query("SELECT DISTINCT year FROM users WHERE role='student' AND year IS NOT NULL ORDER BY year")
    return render_template('admin/notices.html', admin=admin, notices=rows, branches=branches,batches=batches,hostels=hostels,years=years)


@bp.route('/academics')
@admin_required
def academics():
    admin=_user()
    updates=query("""SELECT cu.*,u.name creator FROM class_updates cu LEFT JOIN users u ON u.id=cu.created_by
                    ORDER BY COALESCE(cu.starts_at,cu.created_at) DESC LIMIT 30""")
    timetable=query("SELECT * FROM timetable ORDER BY branch,year,day_of_week,start_time LIMIT 100")
    branches=query("SELECT DISTINCT branch FROM users WHERE role='student' AND branch IS NOT NULL ORDER BY branch")
    return render_template('admin/academics.html', admin=admin, updates=updates, timetable=timetable, branches=branches)


@bp.post('/academics/update')
@admin_required
def academic_update():
    execute("""INSERT INTO class_updates(title,body,update_type,target_batch,target_branch,target_year,starts_at,created_by)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            (request.form['title'].strip(),request.form['body'].strip(),request.form.get('update_type','general'),
             request.form.get('target_batch') or None,request.form.get('target_branch') or None,
             int(request.form['target_year']) if request.form.get('target_year') else None,
             request.form.get('starts_at') or None,session['user_id']))
    flash('Class update published to matching students.','success')
    return redirect(url_for('admin.academics'))


@bp.post('/academics/timetable')
@admin_required
def timetable_create():
    execute("""INSERT INTO timetable(branch,year,day_of_week,start_time,end_time,subject,room,teacher_name,section)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (request.form['branch'],int(request.form['year']),int(request.form['day_of_week']),request.form['start_time'],
             request.form['end_time'],request.form['subject'].strip(),request.form.get('room','').strip(),request.form.get('teacher_name','').strip(),request.form.get('section','A').strip()))
    flash('Timetable entry added.','success')
    return redirect(url_for('admin.academics'))


@bp.route('/finance', methods=['GET','POST'])
@admin_required
def finance():
    admin=_user(); q=request.args.get('q','').strip()
    sql="SELECT u.id,u.name,u.student_id,u.course,u.branch,u.year,u.hostel,COALESCE(f.total_dues,0) total_dues,COALESCE(f.amount_paid,0) amount_paid,COALESCE(f.amount_refunded,0) amount_refunded, GREATEST(COALESCE(f.total_dues,0)-COALESCE(f.amount_paid,0)-COALESCE(f.amount_refunded,0),0) remaining FROM users u LEFT JOIN fee_accounts f ON f.student_id=u.id WHERE u.role='student'"
    params=[]
    if q:
        sql += " AND (u.name LIKE %s OR u.student_id LIKE %s OR u.email LIKE %s OR u.branch LIKE %s OR u.course LIKE %s)"
        params=[f'%{q}%']*5
    sql += " ORDER BY u.name LIMIT 500"
    students=query(sql,tuple(params))
    return render_template('admin/finance.html', admin=admin, students=students, q=q)


@bp.post('/finance/<int:student_id>')
@admin_required
def finance_update(student_id):
    total=float(request.form.get('total_dues',0) or 0); paid=float(request.form.get('amount_paid',0) or 0); refunded=float(request.form.get('amount_refunded',0) or 0)
    execute("INSERT INTO fee_accounts(student_id,total_dues,amount_paid,amount_refunded) VALUES(%s,%s,%s,%s) ON DUPLICATE KEY UPDATE total_dues=VALUES(total_dues),amount_paid=VALUES(amount_paid),amount_refunded=VALUES(amount_refunded)", (student_id,total,paid,refunded))
    flash('Fee account updated.','success')
    return redirect(url_for('admin.finance'))


@bp.route('/users')
@admin_required
def users():
    admin=_user()
    q=request.args.get('q','').strip()
    role=request.args.get('role','all')
    where=[]; params=[]
    if q:
        where.append("(u.name LIKE %s OR u.email LIKE %s OR u.student_id LIKE %s)"); params += [f'%{q}%',f'%{q}%',f'%{q}%']
    if role!='all' and role in ('student','teacher','warden','admin'):
        where.append("u.role=%s"); params.append(role)
    sql="SELECT u.*, (SELECT COUNT(*) FROM complaints c WHERE c.student_id=u.id AND c.status NOT IN ('resolved','rejected')) open_complaints FROM users u"
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY FIELD(u.role,'admin','teacher','warden','student'),u.name LIMIT 300"
    rows=query(sql,tuple(params))
    return render_template('admin/users.html', admin=admin, users=rows, q=q, role=role)


@bp.post('/users/<int:user_id>/toggle')
@admin_required
def user_toggle(user_id):
    if user_id == session['user_id']:
        flash('You cannot deactivate your own administrator account.','warning')
    else:
        execute("UPDATE users SET active=IF(active=1,0,1) WHERE id=%s", (user_id,))
        flash('User account status updated.','success')
    return redirect(request.referrer or url_for('admin.users'))


@bp.route('/hostel')
@admin_required
def hostel():
    admin=_user()
    rooms=query("""SELECT r.*,COUNT(a.id) asset_types,COALESCE(SUM(a.quantity),0) asset_qty
                  FROM rooms r LEFT JOIN assets a ON a.room_id=r.id GROUP BY r.id ORDER BY r.hostel,r.room_no""")
    assets=query("""SELECT a.*,r.hostel,r.room_no FROM assets a JOIN rooms r ON r.id=a.room_id ORDER BY r.hostel,r.room_no,a.asset_name""")
    visitors=query("""SELECT vp.*,u.name student_name,u.student_id FROM visitor_passes vp JOIN users u ON u.id=vp.student_id
                    ORDER BY (vp.status='pending') DESC,vp.created_at DESC LIMIT 40""")
    return render_template('admin/hostel.html', admin=admin, rooms=rooms, assets=assets, visitors=visitors)


@bp.post('/visitors/<int:visit_id>/decision')
@admin_required
def visitor_decision(visit_id):
    status=request.form.get('status')
    if status not in ('approved','rejected','used','expired','pending'): status='pending'
    execute("UPDATE visitor_passes SET status=%s,approved_by=%s WHERE id=%s", (status,session['user_id'],visit_id))
    flash('Visitor pass updated.','success')
    return redirect(url_for('admin.hostel'))
