from datetime import date, datetime, timedelta, time
from werkzeug.security import generate_password_hash
from app import create_app
from app.db import get_db

app=create_app()

BRANCHES=[
    ('Computer Science & Engineering','B.Tech'),('Information Technology','B.Tech'),('Electronics & Communication Engineering','B.Tech'),
    ('Electrical Engineering','B.Tech'),('Civil Engineering','B.Tech'),('Mechanical Engineering','B.Tech'),('Artificial Intelligence & Data Science','B.Tech'),
    ('Computer Science','Diploma'),('Electrical','Diploma'),('Civil','Diploma'),('Computer Applications','BCA/MCA'),('Business Administration','MBA'),('Computer Science & Engineering','M.Tech')
]
COURSES=['B.Tech','Diploma','MBA','MCA','M.Tech','BCA']
HOSTELS=['Boys Hostel A','Boys Hostel B','Boys Hostel C','Girls Hostel A']
SERVICE_DEPTS=['Electrical','IT Services','Civil Works','Furniture','Plumbing','Housekeeping','Security','Mess','Facilities','Network & Lab','Academic Support','Transport']
FIRST=['Aarav','Ananya','Aditya','Anika','Arjun','Avni','Ayush','Diya','Dev','Ishita','Kabir','Kiara','Krishna','Meera','Mohan','Nandini','Neeraj','Pallavi','Pranav','Priya','Rahul','Riya','Rohan','Sakshi','Samar','Sana','Sarthak','Shreya','Siddharth','Simran','Tanmay','Tanya','Utkarsh','Vaishnavi','Varun','Vikas','Yash','Zoya','Aditi','Anmol','Bhavya','Chandan','Deepak','Gargi','Harsh','Jatin','Karan','Muskan','Nikhil']
LAST=['Das','Patnaik','Mohanty','Sahu','Behera','Nayak','Rout','Jena','Pradhan','Mishra','Singh','Dutta']

with app.app_context():
  with get_db() as conn:
    cur=conn.cursor()
    cur.execute('SET FOREIGN_KEY_CHECKS=0')
    for table in ['notification_reads','notice_reads','gate_logs','visitor_passes','mess_feedback','mess_menu','assets','rooms','complaints','document_requests','leave_requests','class_updates','timetable','attendance','fee_accounts','notices','users']:
      cur.execute(f'TRUNCATE TABLE {table}')
    cur.execute('SET FOREIGN_KEY_CHECKS=1')

    pw={
      'admin':generate_password_hash('Admin@123'),'teacher':generate_password_hash('Teacher@123'),
      'warden':generate_password_hash('Warden@123'),'student':generate_password_hash('Student@123')
    }
    cur.execute("INSERT INTO users(role,name,email,phone,password_hash) VALUES('admin','CODE-NOVA CMS System Admin','admin@gmail.com','9000000000',%s)",(pw['admin'],)); admin_id=cur.lastrowid

    warden_rows=[
      ('warden','Warden Anita Rao','warden@gmail.com','9000000001','Girls Hostel A'),
      ('warden','Warden Bikash Das','warden.b@gmail.com','9000000002','Boys Hostel A'),
      ('warden','Warden Chandan Sahu','warden.c@gmail.com','9000000003','Boys Hostel B'),
      ('warden','Warden Deepa Mohanty','warden.d@gmail.com','9000000004','Boys Hostel C'),
    ]
    warden_ids={}
    for role,name,email,phone,hostel in warden_rows:
      cur.execute("INSERT INTO users(role,name,email,phone,password_hash,hostel) VALUES(%s,%s,%s,%s,%s,%s)",(role,name,email,phone,pw['warden'],hostel)); warden_ids[hostel]=cur.lastrowid

    faculty_specs=[
      ('Prof. S. Rout','teacher@gmail.com','Computer Science & Engineering','Academic Support'),
      ('Prof. P. Dash','prof.dash@gmail.com','Information Technology','IT Services'),
      ('Dr. N. Singh','dr.singh@gmail.com','Electronics & Communication Engineering','Network & Lab'),
      ('Prof. A. Mishra','prof.mishra@gmail.com','Electrical Engineering','Electrical'),
      ('Prof. R. Behera','prof.behera@gmail.com','Civil Engineering','Civil Works'),
      ('Prof. K. Nayak','prof.nayak@gmail.com','Mechanical Engineering','Furniture'),
      ('Prof. M. Jena','prof.jena@gmail.com','Artificial Intelligence & Data Science','IT Services'),
      ('Prof. T. Pradhan','prof.pradhan@gmail.com','Computer Science','Plumbing'),
      ('Prof. V. Mohanty','prof.mohanty@gmail.com','Electrical','Electrical'),
      ('Prof. G. Sahu','prof.sahu@gmail.com','Civil','Housekeeping'),
      ('Prof. H. Patnaik','prof.patnaik@gmail.com','Computer Applications','Security'),
      ('Prof. I. Behera','prof.behera2@gmail.com','Business Administration','Facilities'),
      ('Prof. J. Rout','prof.rout2@gmail.com','Computer Science & Engineering','Transport'),
    ]
    faculty_ids=[]
    for i,(name,email,branch,dept) in enumerate(faculty_specs):
      cur.execute("INSERT INTO users(role,name,email,phone,password_hash,branch,department,year) VALUES('teacher',%s,%s,%s,%s,%s,%s,%s)",(name,email,f'91{9000000010+i}',pw['teacher'],branch,dept,3 if i%3==0 else 2)); faculty_ids.append(cur.lastrowid)

    # 48 students spanning multiple courses/branches/years/batches/hostels
    students=[]
    for i in range(48):
      first=FIRST[i%len(FIRST)]; last=LAST[(i*3)%len(LAST)]; name=f'{first} {last}'
      branch=BRANCHES[i%len(BRANCHES)][0]
      course=COURSES[(i//4)%len(COURSES)]
      # align a few naturally with their course
      if course=='MBA': branch='Business Administration'
      elif course=='MCA': branch='Computer Applications'
      elif course=='BCA': branch='Computer Applications'
      elif course=='M.Tech': branch='Computer Science & Engineering'
      year=(i%4)+1
      batch_start=2023+(i%4)
      batch=f'{batch_start}-{str(batch_start+4)[-2:]}'
      hostel=HOSTELS[i%len(HOSTELS)] if i%5!=0 else None
      room=f"{['A','B','C','D'][i%4]}-{101+(i%18)}" if hostel else None
      sid=f'FRE2026S{i+1:03d}'
      email=f'student{i+1:02d}@gmail.com'
      phone=f'98765{10000+i:05d}'
      cur.execute("INSERT INTO users(role,name,email,phone,password_hash,batch,course,branch,year,hostel,room_no,student_id,preferred_language) VALUES('student',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(name,email,phone,pw['student'],batch,course,branch,year,hostel,room,sid,['en','hi','od'][i%3])); students.append({'id':cur.lastrowid,'name':name,'branch':branch,'year':year,'hostel':hostel,'room':room,'batch':batch,'course':course,'student_id':sid})

    # Dedicated demo identity requested in earlier phase
    cur.execute("UPDATE users SET name='Amlan Das',email='student@gmail.com',phone='9876543210',student_id='FRE2026S999',batch='2023-27',course='B.Tech',branch='Computer Science & Engineering',year=3,hostel='Boys Hostel A',room_no='A-204',preferred_language='en' WHERE id=%s", (students[0]['id'],))
    students[0].update(name='Amlan Das',student_id='FRE2026S999',batch='2023-27',course='B.Tech',branch='Computer Science & Engineering',year=3,hostel='Boys Hostel A',room='A-204')

    # Rooms + assets
    asset_catalog=[('Ceiling Fan','good'),('Study Table','good'),('Chair','good'),('Tube Light','good'),('Wardrobe','fair'),('Mattress','good')]
    room_ids={}
    for hostel in HOSTELS:
      prefix={'Boys Hostel A':'A','Boys Hostel B':'B','Boys Hostel C':'C','Girls Hostel A':'G'}[hostel]
      for n in range(101,115):
        cur.execute("INSERT INTO rooms(hostel,room_no,floor,capacity,warden_name) VALUES(%s,%s,%s,%s,%s)",(hostel,f'{prefix}-{n}', '1' if n<107 else '2', 3, {v:k for k,v in warden_ids.items()}[warden_ids[hostel]] if False else next(x[1] for x in warden_rows if x[4]==hostel)))
        rid=cur.lastrowid; room_ids[(hostel,f'{prefix}-{n}')]=rid
        for j,(asset,cond) in enumerate(asset_catalog):
          cur.execute("INSERT INTO assets(room_id,asset_name,asset_code,quantity,condition_status) VALUES(%s,%s,%s,%s,%s)",(rid,asset,f'{prefix}{n}{j+1}', 1 if asset not in ('Chair','Tube Light') else 2, cond if not (n%7==0 and j==4) else 'damaged'))

    # Attendance for every student: 5 subjects, realistic percentages
    subjects={
      'Computer Science & Engineering':['Data Structures','Database Management Systems','Operating Systems','Python Programming','Computer Networks'],
      'Information Technology':['Web Technology','DBMS','Java','Computer Networks','Software Engineering'],
      'Electronics & Communication Engineering':['Digital Electronics','Signals & Systems','Microprocessors','Communication Systems','Embedded Systems'],
      'Electrical Engineering':['Electrical Machines','Power Systems','Control Systems','Power Electronics','Circuit Theory'],
      'Civil Engineering':['Structural Analysis','Surveying','Concrete Technology','Geotechnical Engineering','Transportation'],
      'Mechanical Engineering':['Thermodynamics','Machine Design','Fluid Mechanics','Manufacturing','Heat Transfer'],
      'Artificial Intelligence & Data Science':['Python','Machine Learning','Statistics','Data Mining','Deep Learning'],
      'Computer Science':['Programming in C','Digital Electronics','Computer Architecture','Data Structures','Networking'],
      'Electrical':['Basic Electrical','Wiring Technology','Electrical Machines','Measurements','Power Distribution'],
      'Civil':['Construction','Surveying','Estimation','Material Science','Environmental Engineering'],
      'Computer Applications':['Programming','Database Systems','Web Development','Software Engineering','Computer Networks'],
      'Business Administration':['Management','Accounting','Marketing','Business Economics','Operations'],
    }
    default_sub=['Professional Communication','Engineering Mathematics','Environmental Studies','Soft Skills','Project Work']
    for i,s in enumerate(students):
      subs=subjects.get(s['branch'],default_sub)
      for j,sub in enumerate(subs):
        total=32+(i+j)%12; present=max(18,total-((i+j*2)%9))
        cur.execute("INSERT INTO attendance(student_id,subject,present_days,total_days) VALUES(%s,%s,%s,%s)",(s['id'],sub,present,total))

    # Timetable across branches/years
    for bi,(branch,_) in enumerate(BRANCHES[:10]):
      for year in range(1,5):
        for d in range(1,6):
          for slot,(st,en) in enumerate([('09:00','10:00'),('10:00','11:00'),('11:15','12:15'),('13:30','14:30')]):
            sub=subjects.get(branch,default_sub)[(slot+d+year)%5]
            teacher=faculty_specs[(bi+slot)%len(faculty_specs)][0]
            cur.execute("INSERT INTO timetable(branch,year,day_of_week,start_time,end_time,subject,room,teacher_name,section) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(branch,year,d,st,en,sub,f'Room {200+slot*10+d}',teacher,'A'))

    today=date.today()
    # Current + upcoming menu entries
    for offset in range(0,4):
      d=today+timedelta(days=offset)
      menu=[('breakfast','Idli, Sambar, Banana'),('lunch','Rice, Dalma, Mixed Vegetable, Curd'),('snacks','Tea, Cutlet, Fruit'),('dinner','Roti, Chana Masala, Rice, Salad')]
      for meal,items in menu:
        cur.execute("INSERT INTO mess_menu(menu_date,meal_type,items) VALUES(%s,%s,%s)",(d,meal,items))

    # Fees for all students
    for i,s in enumerate(students):
      total=50000+(i%6)*12500; paid=total-(i%5)*3500; refund=500 if i%7==0 else 0
      cur.execute("INSERT INTO fee_accounts(student_id,total_dues,amount_paid,amount_refunded) VALUES(%s,%s,%s,%s)",(s['id'],total,paid,refund))

    # Notices from all roles
    notice_data=[
      ('Semester fee payment window','The fee portal is open. Check your dues and payment status before the deadline.','admin',None,None,None,None,'important','Check fees','/student/fees',admin_id),
      ('Library timing update','Reading hall will remain open until 9:00 PM during examination preparation week.','admin',None,None,None,None,'normal',None,None,admin_id),
    ]
    # Add one notice targeted per role
    notice_data += [
      ('CSE extra class','Extra tutorial for Data Structures this Saturday at 10:00 AM.','teacher','2023-27','Computer Science & Engineering',3,None,'normal','View timetable','/student/timetable',faculty_ids[0]),
      ('Hostel electrical inspection','Electrical inspection will take place in all rooms tomorrow. Keep access clear.','warden',None,None,None,'Boys Hostel A','important',None,None,warden_ids['Boys Hostel A']),
      ('Mess feedback drive','Please rate today\'s menu and add suggestions so the mess team can improve.','warden',None,None,None,'Girls Hostel A','normal','Give feedback','/student/mess',warden_ids['Girls Hostel A']),
    ]
    cur.executemany("INSERT INTO notices(title,body,sender_role,target_batch,target_branch,target_year,target_hostel,priority,action_label,action_url,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",notice_data)

    # Class updates
    updates=[
      ('DBMS shifted to Lab 2','Today\'s DBMS practical will be held in Lab 2 instead of Room 204.','room_change','2023-27','Computer Science & Engineering',3,faculty_ids[1]),
      ('Faculty absent','Computer Networks class is suspended today because the faculty is unavailable.','teacher_absent',None,'Computer Science & Engineering',3,faculty_ids[2]),
      ('Extra civil tutorial','Extra tutorial on Structural Analysis will be conducted on Friday.','extra_class',None,'Civil Engineering',2,faculty_ids[4]),
      ('Mechanical lab room change','Workshop practical moved to Mechanical Lab B.','room_change',None,'Mechanical Engineering',3,faculty_ids[5]),
    ]
    for title,body,typ,batch,branch,year,creator in updates:
      cur.execute("INSERT INTO class_updates(title,body,update_type,target_batch,target_branch,target_year,starts_at,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(title,body,typ,batch,branch,year,datetime.now()+timedelta(days=1),creator))

    # Leave / gate + document requests
    for i,s in enumerate(students[:18]):
      typ='gate_pass' if i%3==0 else 'leave'; route='warden' if s['hostel'] else 'teacher'
      cur.execute("INSERT INTO leave_requests(student_id,request_type,reason,start_at,end_at,destination,emergency_contact,approval_route,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(s['id'],typ,'Family visit / personal requirement',datetime.now()+timedelta(days=i%4+1),datetime.now()+timedelta(days=i%4+1,hours=8),'Cuttack' if typ=='gate_pass' else 'Home','98'+str(700000000+i).zfill(8),route,'pending' if i%4 else 'approved'))
    for i,s in enumerate(students[10:25]):
      cur.execute("INSERT INTO document_requests(student_id,document_type,purpose,copies,delivery_mode,status) VALUES(%s,%s,%s,%s,%s,%s)",(s['id'],['Bonafide Certificate','Character Certificate','Migration Certificate','Study Certificate'][i%4],'Higher studies / scholarship / internship',1+(i%2),['digital','physical','both'][i%3],['pending','processing','ready'][i%3]))

    # Complaints distributed across service departments
    cats=[('electrical','Fan not working',2,'Electrical'),('internet','Wi-Fi intermittent',1,'IT Services'),('civil','Bathroom tile leakage',4,'Civil Works'),('furniture','Chair broken',3,'Furniture'),('plumbing','Water tap leaking',2,'Plumbing'),('cleaning','Room cleaning pending',1,'Housekeeping'),('security','Visitor entry issue',2,'Security'),('mess','Dinner quality issue',1,'Mess')]
    for i,s in enumerate(students[:32]):
      cat,title,days,dept=cats[i%len(cats)]; ticket=f'FBX-2026-{i+1:04d}'
      status=['submitted','approved','in_progress','approved_not_resolved','resolved'][i%5]
      assigned=faculty_ids[i%len(faculty_ids)]
      created=datetime.now()-timedelta(days=days+(i%3))
      cur.execute("INSERT INTO complaints(ticket_no,student_id,category,title,details,room_no,started_days,department,assigned_to,status,created_at,resolved_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(ticket,s['id'],cat,title,f'{title}. Reported from room {s["room"] or "campus"}.',s['room'],days,dept,assigned,status,created,datetime.now()-timedelta(days=1) if status=='resolved' else None))

    # Visitor passes + gate logs
    for i,s in enumerate([x for x in students if x['hostel']][:20]):
      cur.execute("INSERT INTO visitor_passes(student_id,visitor_name,relation,phone,visit_date,purpose,status,approved_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(s['id'],f'Visitor {i+1}','Parent',f'88990{10000+i:05d}',today+timedelta(days=i%3),'Family visit',['pending','approved','used'][i%3],warden_ids.get(s['hostel'])))
      pid=cur.lastrowid
      if i%3:
        cur.execute("INSERT INTO gate_logs(student_id,pass_type,reference_id,direction,scanned_at,verified_by) VALUES(%s,'visitor',%s,'out',NOW()-INTERVAL %s HOUR,%s)",(s['id'],pid,i+1,warden_ids.get(s['hostel'])))
        cur.execute("INSERT INTO gate_logs(student_id,pass_type,reference_id,direction,scanned_at,verified_by) VALUES(%s,'visitor',%s,'in',NOW()-INTERVAL %s HOUR,%s)",(s['id'],pid,max(1,i),warden_ids.get(s['hostel'])))

    # Mess feedback across hostels
    for i,s in enumerate([x for x in students if x['hostel']][:18]):
      cur.execute("INSERT INTO mess_feedback(student_id,menu_date,rating,suggestion) VALUES(%s,%s,%s,%s)",(s['id'],today,2+(i%4),['More fruit please','Keep breakfast less oily','Add local Odia item','Dinner was good', 'Improve chapati consistency'][i%5]))

    # Read/action tracking for a sample
    cur.execute("SELECT id FROM notices ORDER BY id LIMIT 3")
    notice_ids=[r[0] for r in cur.fetchall()]
    for i,s in enumerate(students[:20]):
      for nid in notice_ids[:1+(i%3)]:
        cur.execute("INSERT INTO notification_reads(notice_id,student_id,read_at,action_taken) VALUES(%s,%s,NOW(),%s) ON DUPLICATE KEY UPDATE action_taken=VALUES(action_taken)",(nid,s['id'],1 if i%2 else 0))

    cur.close()
  print('CODE-NOVA CMS full demo seed complete.')
  print('Admin: admin@gmail.com / Admin@123')
  print('Teacher: teacher@gmail.com / Teacher@123')
  print('Warden: warden@gmail.com / Warden@123')
  print('Student: student@gmail.com / Student@123')
  print('Additional student accounts: student01@gmail.com ... student48@gmail.com / Student@123')
