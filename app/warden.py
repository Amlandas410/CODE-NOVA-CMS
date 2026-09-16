from datetime import date
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .auth import login_required
from .db import query, execute

bp=Blueprint('warden', __name__, url_prefix='/warden')


def warden_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get('role')!='warden':
            flash('Hostel Warden access required.', 'danger'); return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def me(): return query("SELECT * FROM users WHERE id=%s AND role='warden'", (session['user_id'],), one=True)

@bp.route('/')
@bp.route('/dashboard')
@warden_required
def dashboard():
    w=me(); hostel=w['hostel']
    kpis={
      'residents':query("SELECT COUNT(*) c FROM users WHERE role='student' AND hostel=%s",(hostel,),one=True)['c'],
      'pending_requests':query("SELECT COUNT(*) c FROM leave_requests lr JOIN users u ON u.id=lr.student_id WHERE lr.status='pending' AND u.hostel=%s",(hostel,),one=True)['c'],
      'visitor_pending':query("SELECT COUNT(*) c FROM visitor_passes vp JOIN users u ON u.id=vp.student_id WHERE vp.status='pending' AND u.hostel=%s",(hostel,),one=True)['c'],
      'open_complaints':query("SELECT COUNT(*) c FROM complaints c JOIN users u ON u.id=c.student_id WHERE u.hostel=%s AND c.status NOT IN ('resolved','rejected')",(hostel,),one=True)['c'],
    }
    reqs=query("SELECT lr.*,u.name student_name,u.student_id,u.room_no FROM leave_requests lr JOIN users u ON u.id=lr.student_id WHERE lr.approval_route='warden' AND u.hostel=%s ORDER BY (lr.status='pending') DESC,lr.created_at DESC LIMIT 10",(hostel,))
    visitors=query("SELECT vp.*,u.name student_name,u.student_id,u.room_no FROM visitor_passes vp JOIN users u ON u.id=vp.student_id WHERE u.hostel=%s ORDER BY (vp.status='pending') DESC,vp.visit_date DESC LIMIT 10",(hostel,))
    feedback=query("SELECT mf.*,u.name student_name FROM mess_feedback mf JOIN users u ON u.id=mf.student_id WHERE u.hostel=%s ORDER BY mf.created_at DESC LIMIT 8",(hostel,))
    return render_template('warden/dashboard.html',warden=w,kpis=kpis,requests=reqs,visitors=visitors,feedback=feedback)

@bp.route('/requests')
@warden_required
def requests_page():
    w=me(); rows=query("SELECT lr.*,u.name student_name,u.student_id,u.room_no,u.year FROM leave_requests lr JOIN users u ON u.id=lr.student_id WHERE lr.approval_route='warden' AND u.hostel=%s ORDER BY (lr.status='pending') DESC,lr.created_at DESC",(w['hostel'],))
    return render_template('warden/requests.html',warden=w,requests=rows)

@bp.post('/requests/<int:req_id>/decision')
@warden_required
def request_decision(req_id):
    w=me(); status=request.form.get('status') if request.form.get('status') in ('approved','rejected') else 'pending'
    execute("UPDATE leave_requests lr JOIN users u ON u.id=lr.student_id SET lr.status=%s,lr.decision_note=%s,lr.decided_by=%s,lr.decided_at=NOW() WHERE lr.id=%s AND lr.approval_route='warden' AND u.hostel=%s",(status,request.form.get('decision_note','').strip(),w['id'],req_id,w['hostel']))
    flash('Hostel request decision recorded.','success'); return redirect(url_for('warden.requests_page'))

@bp.route('/visitors')
@warden_required
def visitors():
    w=me(); rows=query("SELECT vp.*,u.name student_name,u.student_id,u.room_no FROM visitor_passes vp JOIN users u ON u.id=vp.student_id WHERE u.hostel=%s ORDER BY (vp.status='pending') DESC,vp.visit_date DESC",(w['hostel'],))
    logs=query("SELECT gl.*,u.name student_name,u.student_id,u.room_no FROM gate_logs gl JOIN users u ON u.id=gl.student_id WHERE u.hostel=%s ORDER BY gl.scanned_at DESC LIMIT 60",(w['hostel'],))
    return render_template('warden/visitors.html',warden=w,visitors=rows,logs=logs)

@bp.post('/visitors/<int:visit_id>')
@warden_required
def visitor_decision(visit_id):
    w=me(); status=request.form.get('status') if request.form.get('status') in ('approved','rejected','used','expired') else 'pending'
    execute("UPDATE visitor_passes vp JOIN users u ON u.id=vp.student_id SET vp.status=%s,vp.approved_by=%s WHERE vp.id=%s AND u.hostel=%s",(status,w['id'],visit_id,w['hostel']))
    flash('Visitor pass updated.','success'); return redirect(url_for('warden.visitors'))

@bp.route('/complaints')
@warden_required
def complaints():
    w=me(); rows=query("SELECT c.*,u.name student_name,u.student_id,u.room_no,DATEDIFF(COALESCE(c.resolved_at,NOW()),c.created_at) age_days FROM complaints c JOIN users u ON u.id=c.student_id WHERE u.hostel=%s ORDER BY (c.status='approved_not_resolved') DESC,age_days DESC,c.created_at DESC",(w['hostel'],))
    return render_template('warden/complaints.html',warden=w,complaints=rows)

@bp.post('/complaints/<int:complaint_id>')
@warden_required
def complaint_update(complaint_id):
    w=me(); status=request.form.get('status')
    if status not in ('approved','in_progress','approved_not_resolved','rejected','resolved'): status='in_progress'
    if status=='resolved': execute("UPDATE complaints c JOIN users u ON u.id=c.student_id SET c.status='resolved',c.assigned_to=%s,c.resolved_at=NOW() WHERE c.id=%s AND u.hostel=%s",(w['id'],complaint_id,w['hostel']))
    else: execute("UPDATE complaints c JOIN users u ON u.id=c.student_id SET c.status=%s,c.assigned_to=%s,c.resolved_at=NULL WHERE c.id=%s AND u.hostel=%s",(status,w['id'],complaint_id,w['hostel']))
    flash('Hostel complaint updated.','success'); return redirect(url_for('warden.complaints'))

@bp.route('/mess',methods=['GET','POST'])
@warden_required
def mess():
    w=me()
    if request.method=='POST':
        execute("INSERT INTO mess_menu(menu_date,meal_type,items) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE items=VALUES(items)",(request.form['menu_date'],request.form['meal_type'],request.form['items'].strip()))
        flash('Mess menu updated.','success'); return redirect(url_for('warden.mess'))
    menu=query("SELECT * FROM mess_menu ORDER BY menu_date DESC,FIELD(meal_type,'breakfast','lunch','snacks','dinner') LIMIT 30")
    feedback=query("SELECT mf.*,u.name student_name,u.room_no FROM mess_feedback mf JOIN users u ON u.id=mf.student_id WHERE u.hostel=%s ORDER BY mf.created_at DESC LIMIT 50",(w['hostel'],))
    return render_template('warden/mess.html',warden=w,menu=menu,feedback=feedback,today=date.today().isoformat())


@bp.route('/rooms', methods=['GET','POST'])
@warden_required
def rooms():
    w=me()
    if request.method=='POST':
        action=request.form.get('action')
        if action=='room':
            room_no=request.form['room_no'].strip(); floor=request.form.get('floor','1').strip(); capacity=max(1,int(request.form.get('capacity',3)))
            execute("INSERT INTO rooms(hostel,room_no,floor,capacity,warden_name) VALUES(%s,%s,%s,%s,%s)",(w['hostel'],room_no,floor,capacity,w['name']))
            flash('Room added to your hostel register.','success')
        elif action=='asset':
            room_id=int(request.form['room_id']); execute("INSERT INTO assets(room_id,asset_name,asset_code,quantity,condition_status) SELECT r.id,%s,%s,%s,%s FROM rooms r WHERE r.id=%s AND r.hostel=%s",(request.form['asset_name'].strip(),request.form.get('asset_code','').strip(),max(1,int(request.form.get('quantity',1))),request.form.get('condition_status','good'),room_id,w['hostel']))
            flash('Asset added to the selected room.','success')
        return redirect(url_for('warden.rooms'))
    rooms=query("SELECT r.*,COUNT(a.id) asset_types,COALESCE(SUM(a.quantity),0) asset_qty FROM rooms r LEFT JOIN assets a ON a.room_id=r.id WHERE r.hostel=%s GROUP BY r.id ORDER BY r.room_no",(w['hostel'],))
    assets=query("SELECT a.*,r.room_no FROM assets a JOIN rooms r ON r.id=a.room_id WHERE r.hostel=%s ORDER BY r.room_no,a.asset_name",(w['hostel'],))
    return render_template('warden/rooms.html',warden=w,rooms=rooms,assets=assets)


@bp.post('/gate-scan')
@warden_required
def gate_scan():
    w=me(); identity=request.form.get('student_id','').strip(); direction=request.form.get('direction','out')
    if direction not in ('out','in'): direction='out'
    student=query("SELECT id,name,student_id,hostel FROM users WHERE role='student' AND (student_id=%s OR email=%s) AND hostel=%s AND active=1",(identity,identity,w['hostel']),one=True)
    if not student:
        flash('Student not found in your assigned hostel.','danger'); return redirect(url_for('warden.visitors'))
    pass_row=query("SELECT id,request_type FROM leave_requests WHERE student_id=%s AND request_type='gate_pass' AND status='approved' ORDER BY created_at DESC LIMIT 1",(student['id'],),one=True)
    if not pass_row:
        visitor=query("SELECT id FROM visitor_passes WHERE student_id=%s AND status='approved' ORDER BY visit_date DESC,created_at DESC LIMIT 1",(student['id'],),one=True)
        ptype='visitor' if visitor else 'gate_pass'; ref=visitor['id'] if visitor else None
    else:
        ptype='gate_pass'; ref=pass_row['id']
    execute("INSERT INTO gate_logs(student_id,pass_type,reference_id,direction,verified_by) VALUES(%s,%s,%s,%s,%s)",(student['id'],ptype,ref,direction,w['id']))
    flash(f'Gate {direction.upper()} recorded for {student["name"]}.','success'); return redirect(url_for('warden.visitors'))

@bp.route('/notices',methods=['GET','POST'])
@warden_required
def notices():
    w=me()
    if request.method=='POST':
        execute("INSERT INTO notices(title,body,sender_role,target_batch,target_branch,target_year,target_hostel,priority,action_label,action_url,created_by) VALUES(%s,%s,'warden',%s,NULL,%s,%s,%s,%s,%s,%s)",(request.form['title'].strip(),request.form['body'].strip(),request.form.get('target_batch') or None,int(request.form['target_year']) if request.form.get('target_year') else None,w['hostel'],request.form.get('priority','normal'),request.form.get('action_label') or None,request.form.get('action_url') or None,w['id']))
        flash('Hostel announcement sent.','success'); return redirect(url_for('warden.notices'))
    rows=query("SELECT * FROM notices WHERE created_by=%s ORDER BY created_at DESC LIMIT 30",(w['id'],))
    residents=query("SELECT DISTINCT batch,year FROM users WHERE role='student' AND hostel=%s ORDER BY year,batch",(w['hostel'],))
    return render_template('warden/notices.html',warden=w,notices=rows,residents=residents)
