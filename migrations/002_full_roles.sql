USE code_nova_cms;
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS course VARCHAR(80) NULL AFTER batch;
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(80) NULL AFTER branch;
-- ALTER TABLE attendance ADD UNIQUE KEY unique_student_subject (student_id, subject);


ALTER TABLE users
ADD COLUMN course VARCHAR(80) NULL AFTER batch;
ALTER TABLE users
ADD COLUMN department VARCHAR(80) NULL AFTER branch;
ALTER TABLE attendance
ADD UNIQUE KEY  unique_student_subject (student_id, subject);