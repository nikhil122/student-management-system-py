STUDENT MANAGEMENT SYSTEM
===========================

Project Overview
----------------
Student Management System is a Flask-based web application for managing
students, teachers, courses, attendance, fees, examinations, exam schedules,
results, and user accounts.

Technology Stack
----------------
Backend:
- Python
- Flask
- MySQL
- mysql-connector-python

Frontend:
- HTML
- CSS
- Jinja2 Templates
- JavaScript (where required)

Database:
- MySQL
- Database name: student_management

Authentication
--------------
The system uses the `users` table for authentication.

Supported roles:
- admin : Full system access
- staff  : Staff-level account for future/restricted access

Important:
- Public registration must NOT allow users to choose the role.
- Newly registered users are assigned the `staff` role by default.
- The main admin account should be created manually/securely.
- Passwords must be stored using password hashing, never plain text.

Main Modules
------------
1. Dashboard
   - Total students
   - Total teachers
   - Total courses
   - Active enrollments
   - Total fees collected
   - Today's attendance
   - Total exams
   - Total results
   - Upcoming exams
   - Recent students
   - Recent fee payments
   - Recent results

2. Students
   - Student listing
   - Add student
   - Edit student
   - Student details
   - Student attendance

3. Teachers
   - Teacher listing
   - Add teacher
   - Edit teacher
   - Teacher details

4. Courses
   - Course listing
   - Add course
   - Edit course
   - Course details

5. Attendance
   - Attendance management
   - Mark attendance
   - Attendance reports
   - Student attendance

6. Fees
   - Fee listing
   - Add fee payment
   - Fee details
   - Fee receipt
   - Edit fee

7. Exams
   - Exam management
   - Add exam
   - Edit exam
   - Exam details

8. Exam Schedule
   - Exam schedule management
   - Add schedule
   - Edit schedule
   - Schedule listing

9. Results
   - Result listing
   - Add result
   - Result details
   - Edit result
   - Delete result

10. Profile
    - Update name
    - Update email
    - View username and role
    - Change password

Database Tables
---------------
Important tables currently used by the application include:

- users
- students
- teachers
- courses
- attendance
- fee_payments
- exams
- exam_schedule
- results

Results Table
-------------
The `results` table contains:

- id
- student_id
- exam_id
- subject
- marks
- max_marks
- grade
- remarks
- created_at

Foreign keys:
- student_id -> students.id
- exam_id -> exams.id

Exams Table
-----------
The `exams` table contains:

- id
- exam_name
- exam_date
- description
- status
- created_at

Exam status values:
- Scheduled
- Completed
- Cancelled

Users Table
-----------
The `users` table contains:

- id
- name
- username
- email
- password
- role
- status
- created_at
- updated_at

Role values:
- admin
- staff

Security Notes
--------------
- Use `generate_password_hash()` when creating/updating passwords.
- Use `check_password_hash()` when validating passwords.
- Use parameterized SQL queries.
- Do not store plain-text passwords.
- Do not expose password hashes in templates.
- Public registration should always create staff accounts.
- Admin-only functionality should be protected using the session role.

Session
-------
Typical logged-in session values:

- user_id
- name
- username
- role

The user should be redirected to the login page when not authenticated.

UI / Design
-----------
The application uses a shared layout through:

- base.html
- shared sidebar
- shared header/layout
- static/css/style.css

The design should remain consistent across all modules.

Sidebar Sections
----------------
MAIN
- Dashboard

MANAGEMENT
- Students
- Teachers
- Courses
- Attendance
- Fees

ACADEMIC
- Exams
- Exam Schedule
- Results

ACCOUNT
- Profile
- Logout

Important Development Notes
----------------------------
- Keep existing route names consistent with template `url_for()` calls.
- When adding a new page, create both the Flask route and its template.
- Avoid duplicate Flask endpoint names.
- If a template uses `url_for('example')`, an endpoint named `example`
  must exist in `app.py`.
- When adding database foreign keys, referenced and referencing columns
  must have compatible types and indexes.
- Existing UI/design should not be replaced unnecessarily.

Common Flask BuildError
-----------------------
If an error such as:

    BuildError: Could not build url for endpoint 'add_exam'

appears, check that the corresponding route/function exists in `app.py`.

Example:

    @app.route("/exams/add")
    def add_exam():
        ...

The endpoint will normally be `add_exam`.

Project Run
-----------
Create/activate the virtual environment and install dependencies.

Example:

    python -m venv venv

Windows:

    venv\Scripts\activate

Install required packages:

    pip install flask mysql-connector-python werkzeug

Run the application:

    python app.py

Typical local URL:

    http://localhost:5000/

Database Configuration
----------------------
Configure the MySQL connection in the project's existing database
connection function/configuration.

Typical values:

- Host: localhost
- Database: student_management
- Username: your MySQL username
- Password: your MySQL password

Do not commit real database passwords or secret credentials to Git.

Current Project Status
----------------------
Core modules completed:

- Dashboard
- Students
- Teachers
- Courses
- Attendance
- Fees
- Exams
- Exam Schedule
- Results
- Profile
- Login
- Registration structure with default staff role

Recommended Next Steps
----------------------
- Final full-system testing
- Role-based permissions for staff
- Authentication/security review
- Form validation review
- Responsive/mobile testing
- Database backup strategy
- Error handling cleanup
- Production deployment configuration

END OF README
