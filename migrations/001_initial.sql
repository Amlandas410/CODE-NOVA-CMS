CREATE DATABASE IF NOT EXISTS code_nova_cms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE code_nova_cms;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  role ENUM('student','teacher','warden','admin') NOT NULL,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(160) UNIQUE NOT NULL,
  phone VARCHAR(20),
  password_hash VARCHAR(255) NOT NULL,
  batch VARCHAR(30),
  branch VARCHAR(80),
  year INT,
  hostel VARCHAR(80),
  room_no VARCHAR(30),
  student_id VARCHAR(40) UNIQUE,
  preferred_language VARCHAR(5) DEFAULT 'en',
  active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  subject VARCHAR(120) NOT NULL,
  present_days INT NOT NULL DEFAULT 0,
  total_days INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS timetable (
  id INT AUTO_INCREMENT PRIMARY KEY,
  branch VARCHAR(80) NOT NULL,
  year INT NOT NULL,
  day_of_week TINYINT NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  subject VARCHAR(120) NOT NULL,
  room VARCHAR(50),
  teacher_name VARCHAR(120),
  section VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS class_updates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(160) NOT NULL,
  body TEXT NOT NULL,
  update_type ENUM('room_change','class_suspend','class_change','teacher_absent','extra_class','general') DEFAULT 'general',
  target_batch VARCHAR(30),
  target_branch VARCHAR(80),
  target_year INT,
  starts_at DATETIME,
  created_by INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS leave_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  request_type ENUM('leave','gate_pass') NOT NULL,
  reason TEXT NOT NULL,
  start_at DATETIME NOT NULL,
  end_at DATETIME NOT NULL,
  destination VARCHAR(255),
  emergency_contact VARCHAR(30),
  approval_route ENUM('teacher','warden','admin') NOT NULL,
  status ENUM('pending','approved','rejected') DEFAULT 'pending',
  decision_note TEXT,
  decided_by INT,
  decided_at DATETIME,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (decided_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS document_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  document_type VARCHAR(120) NOT NULL,
  purpose TEXT NOT NULL,
  copies INT DEFAULT 1,
  delivery_mode ENUM('digital','physical','both') DEFAULT 'digital',
  status ENUM('pending','processing','ready','rejected') DEFAULT 'pending',
  admin_note TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fee_accounts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT UNIQUE NOT NULL,
  total_dues DECIMAL(12,2) DEFAULT 0,
  amount_paid DECIMAL(12,2) DEFAULT 0,
  amount_refunded DECIMAL(12,2) DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notices (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(180) NOT NULL,
  body TEXT NOT NULL,
  sender_role ENUM('admin','teacher','warden') NOT NULL,
  target_batch VARCHAR(30),
  target_branch VARCHAR(80),
  target_year INT,
  target_hostel VARCHAR(80),
  priority ENUM('normal','important','urgent') DEFAULT 'normal',
  action_label VARCHAR(80),
  action_url VARCHAR(255),
  created_by INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notice_reads (
  notice_id INT NOT NULL,
  student_id INT NOT NULL,
  read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  action_taken TINYINT(1) DEFAULT 0,
  PRIMARY KEY (notice_id, student_id),
  FOREIGN KEY (notice_id) REFERENCES notices(id) ON DELETE CASCADE,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rooms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  hostel VARCHAR(80) NOT NULL,
  room_no VARCHAR(30) NOT NULL,
  floor VARCHAR(30),
  capacity INT DEFAULT 1,
  warden_name VARCHAR(120)
);

CREATE TABLE IF NOT EXISTS assets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  room_id INT NOT NULL,
  asset_name VARCHAR(120) NOT NULL,
  asset_code VARCHAR(60),
  quantity INT DEFAULT 1,
  condition_status ENUM('good','fair','damaged','missing') DEFAULT 'good',
  FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS complaints (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ticket_no VARCHAR(30) UNIQUE NOT NULL,
  student_id INT NOT NULL,
  category ENUM('electrical','plumbing','civil','internet','cleaning','furniture','mess','security','other') NOT NULL,
  title VARCHAR(160) NOT NULL,
  details TEXT NOT NULL,
  room_no VARCHAR(30),
  started_days INT DEFAULT 0,
  department VARCHAR(80),
  assigned_to INT,
  status ENUM('submitted','approved','in_progress','approved_not_resolved','rejected','resolved') DEFAULT 'submitted',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolved_at DATETIME,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS mess_menu (
  id INT AUTO_INCREMENT PRIMARY KEY,
  menu_date DATE NOT NULL,
  meal_type ENUM('breakfast','lunch','snacks','dinner') NOT NULL,
  items TEXT NOT NULL,
  UNIQUE KEY unique_meal_day (menu_date, meal_type)
);

CREATE TABLE IF NOT EXISTS mess_feedback (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  menu_date DATE NOT NULL,
  rating TINYINT NOT NULL,
  suggestion TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY student_feedback_day (student_id, menu_date)
);

CREATE TABLE IF NOT EXISTS visitor_passes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  visitor_name VARCHAR(120) NOT NULL,
  relation VARCHAR(80),
  phone VARCHAR(20) NOT NULL,
  visit_date DATE NOT NULL,
  in_time TIME,
  out_time TIME,
  purpose TEXT NOT NULL,
  status ENUM('pending','approved','rejected','used','expired') DEFAULT 'pending',
  approved_by INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS gate_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  pass_type ENUM('gate_pass','visitor') NOT NULL,
  reference_id INT,
  direction ENUM('out','in') NOT NULL,
  scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  verified_by INT,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notification_reads (
  id INT AUTO_INCREMENT PRIMARY KEY,
  notice_id INT NOT NULL,
  student_id INT NOT NULL,
  read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  action_taken TINYINT(1) DEFAULT 0,
  UNIQUE KEY notification_student (notice_id, student_id),
  FOREIGN KEY (notice_id) REFERENCES notices(id) ON DELETE CASCADE,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
);
