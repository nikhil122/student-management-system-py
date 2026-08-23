from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

from config import DB_CONFIG
import os

from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = "student_management_secret_key"

# =========================
# FILE UPLOAD CONFIG
# =========================

STUDENT_UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "uploads",
    "students"
)

os.makedirs(
    STUDENT_UPLOAD_FOLDER,
    exist_ok=True
)

app.config["STUDENT_UPLOAD_FOLDER"] = STUDENT_UPLOAD_FOLDER


ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

# =========================
# TEACHER UPLOAD CONFIG
# =========================

TEACHER_UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "uploads",
    "teachers"
)

os.makedirs(
    TEACHER_UPLOAD_FOLDER,
    exist_ok=True
)

app.config["TEACHER_UPLOAD_FOLDER"] = TEACHER_UPLOAD_FOLDER


# =========================
# IMAGE VALIDATION FUNCTION
# =========================

def allowed_image(filename):

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_IMAGE_EXTENSIONS



# =========================
# LOGIN PROTECTION
# =========================

PUBLIC_ROUTES = {
    "index",
    "login",
    "register",
    "static"
}


@app.before_request
def login_required():

    # Public pages
    if request.endpoint in PUBLIC_ROUTES:
        return

    # Login check
    if not session.get("user_id"):
        flash(
            "Please login to continue.",
            "danger"
        )

        return redirect(url_for("login"))


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# =========================
# HOME
# =========================

@app.route("/")
def index():
    return render_template("index.html")

# =========================
# AUTHENTICATION
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not username or not email or not password:

            flash(
                "All fields are required.",
                "danger"
            )

            return redirect(url_for("register"))

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(url_for("register"))

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "danger"
            )

            return redirect(url_for("register"))

        try:

            conn = get_db_connection()
            cursor = conn.cursor()

            # Check existing username/email
            cursor.execute("""
                SELECT id
                FROM users
                WHERE username = %s
                   OR email = %s
            """, (
                username,
                email
            ))

            existing_user = cursor.fetchone()

            if existing_user:

                cursor.close()
                conn.close()

                flash(
                    "Username or email already exists.",
                    "danger"
                )

                return redirect(url_for("register"))

            hashed_password = generate_password_hash(
                password
            )

            cursor.execute("""
                INSERT INTO users (
                    name,
                    username,
                    email,
                    password,
                    role,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                name,
                username,
                email,
                hashed_password,
                "admin",
                1
            ))

            conn.commit()

            cursor.close()
            conn.close()

            flash(
                "Registration successful. Please login.",
                "success"
            )

            return redirect(url_for("login"))

        except mysql.connector.Error as error:

            return f"Database Error: {error}", 500

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:

            flash(
                "Username and password are required.",
                "danger"
            )

            return redirect(url_for("login"))

        try:

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT *
                FROM users
                WHERE username = %s
                AND status = 1
                LIMIT 1
            """, (username,))

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if not user:

                flash(
                    "Invalid username or password.",
                    "danger"
                )

                return redirect(url_for("login"))

            if not check_password_hash(
                user["password"],
                password
            ):

                flash(
                    "Invalid username or password.",
                    "danger"
                )

                return redirect(url_for("login"))

            session.clear()

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["username"] = user["username"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        except mysql.connector.Error as error:

            return f"Database Error: {error}", 500

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("login"))

# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # =========================
        # TOTAL STUDENTS
        # =========================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM students
            WHERE status = 'Active'
        """)

        total_students = cursor.fetchone()["total"]


        # =========================
        # TOTAL TEACHERS
        # =========================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM teachers
            WHERE status = 'Active'
        """)

        total_teachers = cursor.fetchone()["total"]


        # =========================
        # TOTAL COURSES
        # =========================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM courses
            WHERE status = 'Active'
        """)

        total_courses = cursor.fetchone()["total"]


        # =========================
        # ACTIVE ENROLLMENTS
        # =========================
        #
        # Current database structure
        # does not contain an enrollment table.
        #
        # So we calculate active students
        # as active enrollments.
        #


        total_enrollments = total_students


        # =========================
        # TOTAL FEES COLLECTED
        # =========================

        cursor.execute("""
            SELECT
                COALESCE(SUM(amount), 0) AS total
            FROM fee_payments
        """)

        total_fees = cursor.fetchone()["total"]


        # =========================
        # TODAY'S ATTENDANCE
        # =========================

        cursor.execute("""
            SELECT
                COUNT(*) AS total_attendance,
                SUM(
                    CASE
                        WHEN status = 'Present'
                        THEN 1
                        ELSE 0
                    END
                ) AS present_count
            FROM attendance
            WHERE attendance_date = CURDATE()
        """)

        attendance_data = cursor.fetchone()


        total_attendance = (
            attendance_data["total_attendance"] or 0
        )

        present_count = (
            attendance_data["present_count"] or 0
        )


        if total_attendance > 0:

            attendance_percentage = round(
                (
                    present_count
                    / total_attendance
                ) * 100,
                2
            )

        else:

            attendance_percentage = 0


        # =========================
        # RECENT STUDENTS
        # =========================

        cursor.execute("""
            SELECT
                id,
                admission_no,
                student_name,
                mobile
            FROM students
            ORDER BY id DESC
            LIMIT 5
        """)

        recent_students = cursor.fetchall()


        # =========================
        # RECENT FEE PAYMENTS
        # =========================

        cursor.execute("""
            SELECT
                fp.id,
                fp.receipt_no,
                fp.amount,
                fp.payment_date,
                s.student_name
            FROM fee_payments fp

            INNER JOIN students s
                ON s.id = fp.student_id

            ORDER BY
                fp.payment_date DESC,
                fp.id DESC

            LIMIT 5
        """)

        recent_fees = cursor.fetchall()

                # =========================
        # TOTAL EXAMS
        # =========================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM exams
        """)

        total_exams = cursor.fetchone()["total"]


        # =========================
        # TOTAL RESULTS
        # =========================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM results
        """)

        total_results = cursor.fetchone()["total"]


        # =========================
        # UPCOMING EXAMS
        # =========================

        cursor.execute("""
            SELECT
                id,
                exam_name,
                exam_date,
                status
            FROM exams
            WHERE exam_date >= CURDATE()
              AND status = 'Scheduled'
            ORDER BY exam_date ASC, id ASC
            LIMIT 5
        """)

        upcoming_exams = cursor.fetchall()


        # =========================
        # RECENT RESULTS
        # =========================

        cursor.execute("""
            SELECT
                r.id,
                r.subject,
                r.marks,
                r.max_marks,
                r.grade,
                s.student_name,
                e.exam_name

            FROM results r

            INNER JOIN students s
                ON s.id = r.student_id

            INNER JOIN exams e
                ON e.id = r.exam_id

            ORDER BY
                r.created_at DESC,
                r.id DESC

            LIMIT 5
        """)

        recent_results = cursor.fetchall()


        cursor.close()
        conn.close()


        return render_template(
            "dashboard.html",

            total_students=total_students,

            total_teachers=total_teachers,

            total_courses=total_courses,

            total_enrollments=total_enrollments,

            total_fees=total_fees,

            attendance_percentage=attendance_percentage,

            total_exams=total_exams,

            total_results=total_results,

            upcoming_exams=upcoming_exams,

            recent_students=recent_students,

            recent_fees=recent_fees,

            recent_results=recent_results
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )


# =========================
# DATABASE TEST
# =========================

@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return f"Database Connected Successfully! Total Students: {total_students}"

    except mysql.connector.Error as error:
        return f"Database Connection Error: {error}"


# =========================
# STUDENT ROUTES
# =========================

@app.route("/students")
def students():

    search = request.args.get("search", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        search_value = f"%{search}%"

        cursor.execute("""
            SELECT *
            FROM students
            WHERE
                admission_no LIKE %s
                OR student_name LIKE %s
                OR father_name LIKE %s
                OR mobile LIKE %s
                OR email LIKE %s
            ORDER BY id DESC
        """, (
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ))

    else:

        cursor.execute("""
            SELECT *
            FROM students
            ORDER BY id DESC
        """)

    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "students.html",
        students=students,
        search=search
    )


@app.route("/students/add", methods=["GET", "POST"])
def add_student():

    if request.method == "POST":

        admission_no = request.form.get(
            "admission_no",
            ""
        ).strip()

        student_name = request.form.get(
            "student_name",
            ""
        ).strip()

        father_name = request.form.get(
            "father_name",
            ""
        ).strip()

        mother_name = request.form.get(
            "mother_name",
            ""
        ).strip()

        dob = request.form.get(
            "dob"
        ) or None

        gender = request.form.get(
            "gender",
            ""
        ).strip()

        mobile = request.form.get(
            "mobile",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        course = request.form.get(
            "course",
            ""
        ).strip()

        semester = request.form.get(
            "semester",
            ""
        ).strip()

        admission_date = request.form.get(
            "admission_date"
        ) or None

        status = request.form.get(
            "status",
            "Active"
        ).strip()


        # =========================
        # VALIDATION
        # =========================

        if not admission_no or not student_name:

            flash(
                "Admission number and student name are required.",
                "danger"
            )

            return redirect(
                url_for("add_student")
            )


        # =========================
        # PHOTO
        # =========================

        photo = request.files.get("photo")

        photo_filename = None


        if photo and photo.filename:

            if not allowed_image(photo.filename):

                flash(
                    "Only JPG, JPEG, PNG and WEBP images are allowed.",
                    "danger"
                )

                return redirect(
                    url_for("add_student")
                )


            original_name = secure_filename(
                photo.filename
            )


            # Unique filename
            import uuid

            extension = original_name.rsplit(
                ".",
                1
            )[1].lower()

            photo_filename = (
                uuid.uuid4().hex
                + "."
                + extension
            )


            photo_path = os.path.join(
                app.config["STUDENT_UPLOAD_FOLDER"],
                photo_filename
            )


            photo.save(photo_path)


        # =========================
        # DATABASE
        # =========================

        try:

            conn = get_db_connection()

            cursor = conn.cursor()


            # Check duplicate admission number

            cursor.execute("""
                SELECT id
                FROM students
                WHERE admission_no = %s
            """, (
                admission_no,
            ))

            existing_student = cursor.fetchone()


            if existing_student:

                cursor.close()
                conn.close()

                # Delete uploaded photo if duplicate

                if photo_filename:

                    uploaded_file = os.path.join(
                        app.config["STUDENT_UPLOAD_FOLDER"],
                        photo_filename
                    )

                    if os.path.exists(
                        uploaded_file
                    ):
                        os.remove(
                            uploaded_file
                        )


                flash(
                    "Admission number already exists.",
                    "danger"
                )

                return redirect(
                    url_for("add_student")
                )


            # Insert student

            cursor.execute("""
                INSERT INTO students (
                    admission_no,
                    student_name,
                    father_name,
                    mother_name,
                    dob,
                    gender,
                    mobile,
                    email,
                    address,
                    course,
                    semester,
                    admission_date,
                    photo,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    NOW(), NOW()
                )
            """, (
                admission_no,
                student_name,
                father_name or None,
                mother_name or None,
                dob,
                gender or None,
                mobile or None,
                email or None,
                address or None,
                course or None,
                semester or None,
                admission_date,
                photo_filename,
                status
            ))


            conn.commit()


            cursor.close()
            conn.close()


            flash(
                "Student added successfully.",
                "success"
            )


            return redirect(
                url_for("students")
            )


        except mysql.connector.Error as error:

            # Delete uploaded photo if DB insert fails

            if photo_filename:

                uploaded_file = os.path.join(
                    app.config["STUDENT_UPLOAD_FOLDER"],
                    photo_filename
                )

                if os.path.exists(
                    uploaded_file
                ):
                    os.remove(
                        uploaded_file
                    )


            return (
                f"Database Error: {error}",
                500
            )


    return render_template(
        "add_student.html"
    )

@app.route("/students/<int:id>")
def student_details(id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Student
        cursor.execute("""
            SELECT *
            FROM students
            WHERE id = %s
        """, (id,))

        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return "Student not found", 404

        # Enrolled courses
        cursor.execute("""
            SELECT
                sc.id,
                sc.enrollment_date,
                sc.status,
                c.course_code,
                c.course_name,
                c.duration,
                c.total_fees
            FROM student_courses sc
            INNER JOIN courses c
                ON c.id = sc.course_id
            WHERE sc.student_id = %s
            ORDER BY sc.id DESC
        """, (id,))

        enrollments = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "student_details.html",
            student=student,
            enrollments=enrollments
        )

    except mysql.connector.Error as error:
        return f"Database Error: {error}", 500


# =========================
# EDIT STUDENT
# =========================

@app.route("/students/edit/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # GET EXISTING STUDENT
        # =========================

        cursor.execute("""
            SELECT
                id,
                admission_no,
                student_name,
                father_name,
                mother_name,
                dob,
                gender,
                mobile,
                email,
                address,
                course,
                semester,
                admission_date,
                photo,
                status,
                created_at,
                updated_at
            FROM students
            WHERE id = %s
        """, (id,))

        student = cursor.fetchone()

        if not student:

            cursor.close()
            conn.close()

            flash(
                "Student not found.",
                "danger"
            )

            return redirect(
                url_for("students")
            )


        # =========================
        # UPDATE
        # =========================

        if request.method == "POST":

            admission_no = request.form.get(
                "admission_no",
                ""
            ).strip()

            student_name = request.form.get(
                "student_name",
                ""
            ).strip()

            father_name = request.form.get(
                "father_name",
                ""
            ).strip()

            mother_name = request.form.get(
                "mother_name",
                ""
            ).strip()

            dob = request.form.get("dob") or None

            gender = request.form.get(
                "gender",
                ""
            ).strip()

            mobile = request.form.get(
                "mobile",
                ""
            ).strip()

            email = request.form.get(
                "email",
                ""
            ).strip()

            address = request.form.get(
                "address",
                ""
            ).strip()

            course = request.form.get(
                "course",
                ""
            ).strip()

            semester = request.form.get(
                "semester",
                ""
            ).strip()

            admission_date = (
                request.form.get(
                    "admission_date"
                ) or None
            )

            status = request.form.get(
                "status",
                "Active"
            ).strip()


            # =========================
            # VALIDATION
            # =========================

            if not admission_no or not student_name:

                cursor.close()
                conn.close()

                flash(
                    "Admission number and student name are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_student",
                        id=id
                    )
                )


            # =========================
            # DUPLICATE ADMISSION NO
            # =========================

            cursor.execute("""
                SELECT id
                FROM students
                WHERE admission_no = %s
                AND id != %s
            """, (
                admission_no,
                id
            ))

            duplicate = cursor.fetchone()

            if duplicate:

                cursor.close()
                conn.close()

                flash(
                    "Admission number already exists.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_student",
                        id=id
                    )
                )


            # =========================
            # PHOTO
            # =========================

            photo = request.files.get("photo")

            new_photo_filename = None

            old_photo_filename = student["photo"]


            if photo and photo.filename:

                if not allowed_image(
                    photo.filename
                ):

                    cursor.close()
                    conn.close()

                    flash(
                        "Only JPG, JPEG, PNG and WEBP images are allowed.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "edit_student",
                            id=id
                        )
                    )


                # Generate unique filename

                import uuid

                original_name = secure_filename(
                    photo.filename
                )

                extension = original_name.rsplit(
                    ".",
                    1
                )[1].lower()

                new_photo_filename = (
                    uuid.uuid4().hex
                    + "."
                    + extension
                )


                photo_path = os.path.join(
                    app.config["STUDENT_UPLOAD_FOLDER"],
                    new_photo_filename
                )


                photo.save(photo_path)


            # =========================
            # UPDATE DATABASE
            # =========================

            if new_photo_filename:

                cursor.execute("""
                    UPDATE students
                    SET
                        admission_no = %s,
                        student_name = %s,
                        father_name = %s,
                        mother_name = %s,
                        dob = %s,
                        gender = %s,
                        mobile = %s,
                        email = %s,
                        address = %s,
                        course = %s,
                        semester = %s,
                        admission_date = %s,
                        photo = %s,
                        status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    admission_no,
                    student_name,
                    father_name or None,
                    mother_name or None,
                    dob,
                    gender or None,
                    mobile or None,
                    email or None,
                    address or None,
                    course or None,
                    semester or None,
                    admission_date,
                    new_photo_filename,
                    status,
                    id
                ))

            else:

                cursor.execute("""
                    UPDATE students
                    SET
                        admission_no = %s,
                        student_name = %s,
                        father_name = %s,
                        mother_name = %s,
                        dob = %s,
                        gender = %s,
                        mobile = %s,
                        email = %s,
                        address = %s,
                        course = %s,
                        semester = %s,
                        admission_date = %s,
                        status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    admission_no,
                    student_name,
                    father_name or None,
                    mother_name or None,
                    dob,
                    gender or None,
                    mobile or None,
                    email or None,
                    address or None,
                    course or None,
                    semester or None,
                    admission_date,
                    status,
                    id
                ))


            conn.commit()


            # =========================
            # DELETE OLD PHOTO
            # =========================

            if new_photo_filename and old_photo_filename:

                old_photo_path = os.path.join(
                    app.config["STUDENT_UPLOAD_FOLDER"],
                    old_photo_filename
                )

                if os.path.exists(
                    old_photo_path
                ):

                    os.remove(
                        old_photo_path
                    )


            cursor.close()
            conn.close()


            flash(
                "Student updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "student_details",
                    id=id
                )
            )


        # =========================
        # GET FORM
        # =========================

        cursor.close()
        conn.close()

        return render_template(
            "edit_student.html",
            student=student
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

@app.route("/students/<int:id>/delete", methods=["POST"])
def delete_student(id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM students
            WHERE id = %s
        """, (id,))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Student deleted successfully.", "success")

        return redirect(url_for("students"))

    except mysql.connector.Error as error:
        return f"Database Error: {error}", 500

    # =========================
# TEACHER ROUTES
# =========================

@app.route("/teachers")
def teachers():

    search = request.args.get("search", "").strip()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if search:
            search_value = f"%{search}%"

            cursor.execute("""
                SELECT *
                FROM teachers
                WHERE
                    teacher_code LIKE %s
                    OR teacher_name LIKE %s
                    OR qualification LIKE %s
                    OR subject LIKE %s
                    OR mobile LIKE %s
                    OR email LIKE %s
                ORDER BY id DESC
            """, (
                search_value,
                search_value,
                search_value,
                search_value,
                search_value,
                search_value
            ))
        else:
            cursor.execute("""
                SELECT *
                FROM teachers
                ORDER BY id DESC
            """)

        teachers = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "teachers.html",
            teachers=teachers,
            search=search
        )

    except mysql.connector.Error as error:
        return f"Database Error: {error}", 500

# =========================
# ADD TEACHER
# =========================

@app.route("/teachers/add", methods=["GET", "POST"])
def add_teacher():

    if request.method == "POST":

        teacher_code = request.form.get(
            "teacher_code",
            ""
        ).strip()

        teacher_name = request.form.get(
            "teacher_name",
            ""
        ).strip()

        qualification = request.form.get(
            "qualification",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        mobile = request.form.get(
            "mobile",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        joining_date = (
            request.form.get(
                "joining_date"
            ) or None
        )

        status = request.form.get(
            "status",
            "Active"
        ).strip()


        # =========================
        # VALIDATION
        # =========================

        if not teacher_code or not teacher_name:

            flash(
                "Teacher code and teacher name are required.",
                "danger"
            )

            return redirect(
                url_for("add_teacher")
            )


        photo = request.files.get("photo")

        photo_filename = None


        # =========================
        # PHOTO
        # =========================

        if photo and photo.filename:

            if not allowed_image(
                photo.filename
            ):

                flash(
                    "Only JPG, JPEG, PNG and WEBP images are allowed.",
                    "danger"
                )

                return redirect(
                    url_for("add_teacher")
                )


            import uuid

            original_name = secure_filename(
                photo.filename
            )

            extension = original_name.rsplit(
                ".",
                1
            )[1].lower()

            photo_filename = (
                uuid.uuid4().hex
                + "."
                + extension
            )


            photo_path = os.path.join(
                app.config["TEACHER_UPLOAD_FOLDER"],
                photo_filename
            )


            photo.save(photo_path)


        # =========================
        # DATABASE
        # =========================

        try:

            conn = get_db_connection()

            cursor = conn.cursor()


            # Duplicate teacher code

            cursor.execute("""
                SELECT id
                FROM teachers
                WHERE teacher_code = %s
            """, (
                teacher_code,
            ))

            existing_teacher = cursor.fetchone()


            if existing_teacher:

                cursor.close()
                conn.close()


                # Remove uploaded photo

                if photo_filename:

                    uploaded_file = os.path.join(
                        app.config["TEACHER_UPLOAD_FOLDER"],
                        photo_filename
                    )

                    if os.path.exists(
                        uploaded_file
                    ):

                        os.remove(
                            uploaded_file
                        )


                flash(
                    "Teacher code already exists.",
                    "danger"
                )

                return redirect(
                    url_for("add_teacher")
                )


            # Insert teacher

            cursor.execute("""
                INSERT INTO teachers (
                    teacher_code,
                    teacher_name,
                    qualification,
                    subject,
                    mobile,
                    email,
                    address,
                    joining_date,
                    photo,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    NOW(), NOW()
                )
            """, (
                teacher_code,
                teacher_name,
                qualification or None,
                subject or None,
                mobile or None,
                email or None,
                address or None,
                joining_date,
                photo_filename,
                status
            ))


            conn.commit()


            cursor.close()
            conn.close()


            flash(
                "Teacher added successfully.",
                "success"
            )


            return redirect(
                url_for("teachers")
            )


        except mysql.connector.Error as error:


            # Remove photo if DB insert fails

            if photo_filename:

                uploaded_file = os.path.join(
                    app.config["TEACHER_UPLOAD_FOLDER"],
                    photo_filename
                )

                if os.path.exists(
                    uploaded_file
                ):

                    os.remove(
                        uploaded_file
                    )


            return (
                f"Database Error: {error}",
                500
            )


    return render_template(
        "add_teacher.html"
    )


@app.route("/teachers/<int:id>")
def teacher_details(id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM teachers
            WHERE id = %s
        """, (id,))

        teacher = cursor.fetchone()

        cursor.close()
        conn.close()

        if not teacher:
            return "Teacher not found", 404

        return render_template(
            "teacher_details.html",
            teacher=teacher
        )

    except mysql.connector.Error as error:
        return f"Database Error: {error}", 500

 # =========================
# EDIT TEACHER
# =========================

@app.route("/teachers/edit/<int:id>", methods=["GET", "POST"])
def edit_teacher(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # GET EXISTING TEACHER
        # =========================

        cursor.execute("""
            SELECT
                id,
                teacher_code,
                teacher_name,
                qualification,
                subject,
                mobile,
                email,
                address,
                joining_date,
                photo,
                status,
                created_at,
                updated_at
            FROM teachers
            WHERE id = %s
        """, (id,))

        teacher = cursor.fetchone()

        if not teacher:

            cursor.close()
            conn.close()

            flash(
                "Teacher not found.",
                "danger"
            )

            return redirect(
                url_for("teachers")
            )


        # =========================
        # UPDATE
        # =========================

        if request.method == "POST":

            teacher_code = request.form.get(
                "teacher_code",
                ""
            ).strip()

            teacher_name = request.form.get(
                "teacher_name",
                ""
            ).strip()

            qualification = request.form.get(
                "qualification",
                ""
            ).strip()

            subject = request.form.get(
                "subject",
                ""
            ).strip()

            mobile = request.form.get(
                "mobile",
                ""
            ).strip()

            email = request.form.get(
                "email",
                ""
            ).strip()

            address = request.form.get(
                "address",
                ""
            ).strip()

            joining_date = (
                request.form.get(
                    "joining_date"
                ) or None
            )

            status = request.form.get(
                "status",
                "Active"
            ).strip()


            # =========================
            # VALIDATION
            # =========================

            if not teacher_code or not teacher_name:

                cursor.close()
                conn.close()

                flash(
                    "Teacher code and teacher name are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_teacher",
                        id=id
                    )
                )


            # =========================
            # DUPLICATE TEACHER CODE
            # =========================

            cursor.execute("""
                SELECT id
                FROM teachers
                WHERE teacher_code = %s
                AND id != %s
            """, (
                teacher_code,
                id
            ))

            duplicate = cursor.fetchone()

            if duplicate:

                cursor.close()
                conn.close()

                flash(
                    "Teacher code already exists.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_teacher",
                        id=id
                    )
                )


            # =========================
            # PHOTO
            # =========================

            photo = request.files.get("photo")

            new_photo_filename = None

            old_photo_filename = teacher["photo"]


            if photo and photo.filename:

                if not allowed_image(
                    photo.filename
                ):

                    cursor.close()
                    conn.close()

                    flash(
                        "Only JPG, JPEG, PNG and WEBP images are allowed.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "edit_teacher",
                            id=id
                        )
                    )


                import uuid

                original_name = secure_filename(
                    photo.filename
                )

                extension = original_name.rsplit(
                    ".",
                    1
                )[1].lower()

                new_photo_filename = (
                    uuid.uuid4().hex
                    + "."
                    + extension
                )


                photo_path = os.path.join(
                    app.config["TEACHER_UPLOAD_FOLDER"],
                    new_photo_filename
                )


                photo.save(photo_path)


            # =========================
            # UPDATE DATABASE
            # =========================

            if new_photo_filename:

                cursor.execute("""
                    UPDATE teachers
                    SET
                        teacher_code = %s,
                        teacher_name = %s,
                        qualification = %s,
                        subject = %s,
                        mobile = %s,
                        email = %s,
                        address = %s,
                        joining_date = %s,
                        photo = %s,
                        status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    teacher_code,
                    teacher_name,
                    qualification or None,
                    subject or None,
                    mobile or None,
                    email or None,
                    address or None,
                    joining_date,
                    new_photo_filename,
                    status,
                    id
                ))

            else:

                cursor.execute("""
                    UPDATE teachers
                    SET
                        teacher_code = %s,
                        teacher_name = %s,
                        qualification = %s,
                        subject = %s,
                        mobile = %s,
                        email = %s,
                        address = %s,
                        joining_date = %s,
                        status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    teacher_code,
                    teacher_name,
                    qualification or None,
                    subject or None,
                    mobile or None,
                    email or None,
                    address or None,
                    joining_date,
                    status,
                    id
                ))


            conn.commit()


            # =========================
            # DELETE OLD PHOTO
            # =========================

            if new_photo_filename and old_photo_filename:

                old_photo_path = os.path.join(
                    app.config["TEACHER_UPLOAD_FOLDER"],
                    old_photo_filename
                )

                if os.path.exists(
                    old_photo_path
                ):

                    os.remove(
                        old_photo_path
                    )


            cursor.close()
            conn.close()


            flash(
                "Teacher updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "teacher_details",
                    id=id
                )
            )


        # =========================
        # GET FORM
        # =========================

        cursor.close()
        conn.close()

        return render_template(
            "edit_teacher.html",
            teacher=teacher
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

# =========================
# DELETE TEACHER
# =========================

@app.route("/teachers/<int:id>/delete", methods=["POST"])
def delete_teacher(id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM teachers
            WHERE id = %s
        """, (id,))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Teacher deleted successfully.", "success")

        return redirect(url_for("teachers"))

    except mysql.connector.Error as error:
        return f"Database Error: {error}", 500

    # =========================
# COURSE ROUTES
# =========================

@app.route("/courses")
def courses():

    search = request.args.get("search", "").strip()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if search:
            search_value = f"%{search}%"

            cursor.execute("""
                SELECT *
                FROM courses
                WHERE
                    course_name LIKE %s
                    OR course_code LIKE %s
                    OR duration LIKE %s
                ORDER BY id DESC
            """, (
                search_value,
                search_value,
                search_value
            ))
        else:
            cursor.execute("""
                SELECT *
                FROM courses
                ORDER BY id DESC
            """)

        courses = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "courses.html",
            courses=courses,
            search=search
        )

    except mysql.connector.Error as error:
        return f"Database Error: {error}", 500

# =========================
# ADD COURSE
# =========================

@app.route("/courses/add", methods=["GET", "POST"])
def add_course():

    if request.method == "POST":

        course_name = request.form.get(
            "course_name",
            ""
        ).strip()

        course_code = request.form.get(
            "course_code",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        total_fees = request.form.get(
            "total_fees",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "Active"
        ).strip()


        # =========================
        # VALIDATION
        # =========================

        if not course_name or not course_code:

            flash(
                "Course name and course code are required.",
                "danger"
            )

            return redirect(
                url_for("add_course")
            )


        # =========================
        # FEES VALIDATION
        # =========================

        if total_fees == "":
            total_fees = 0

        try:

            total_fees = float(total_fees)

            if total_fees < 0:
                raise ValueError

        except ValueError:

            flash(
                "Please enter a valid course fee.",
                "danger"
            )

            return redirect(
                url_for("add_course")
            )


        # =========================
        # DATABASE
        # =========================

        try:

            conn = get_db_connection()

            cursor = conn.cursor()


            # Duplicate Course Code

            cursor.execute("""
                SELECT id
                FROM courses
                WHERE course_code = %s
            """, (
                course_code,
            ))

            existing_course = cursor.fetchone()


            if existing_course:

                cursor.close()
                conn.close()

                flash(
                    "Course code already exists.",
                    "danger"
                )

                return redirect(
                    url_for("add_course")
                )


            # Insert Course

            cursor.execute("""
                INSERT INTO courses (
                    course_name,
                    course_code,
                    duration,
                    total_fees,
                    description,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW(),
                    NOW()
                )
            """, (
                course_name,
                course_code,
                duration or None,
                total_fees,
                description or None,
                status
            ))


            conn.commit()


            cursor.close()
            conn.close()


            flash(
                "Course added successfully.",
                "success"
            )


            return redirect(
                url_for("courses")
            )


        except mysql.connector.Error as error:

            return (
                f"Database Error: {error}",
                500
            )


    return render_template(
        "add_course.html"
    )

# =========================
# COURSE DETAILS
# =========================

@app.route("/courses/<int:id>")
def course_details(id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM courses
            WHERE id = %s
        """, (id,))

        course = cursor.fetchone()

        cursor.close()
        conn.close()

        if not course:
            return "Course not found", 404

        return render_template(
            "course_details.html",
            course=course
        )

    except mysql.connector.Error as error:
        return f"Database Error: {error}", 500

# =========================
# EDIT COURSE
# =========================

@app.route("/courses/edit/<int:id>", methods=["GET", "POST"])
def edit_course(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # GET EXISTING COURSE
        # =========================

        cursor.execute("""
            SELECT
                id,
                course_name,
                course_code,
                duration,
                total_fees,
                description,
                status,
                created_at,
                updated_at
            FROM courses
            WHERE id = %s
        """, (id,))

        course = cursor.fetchone()

        if not course:

            cursor.close()
            conn.close()

            flash(
                "Course not found.",
                "danger"
            )

            return redirect(
                url_for("courses")
            )


        # =========================
        # UPDATE
        # =========================

        if request.method == "POST":

            course_name = request.form.get(
                "course_name",
                ""
            ).strip()

            course_code = request.form.get(
                "course_code",
                ""
            ).strip()

            duration = request.form.get(
                "duration",
                ""
            ).strip()

            total_fees = request.form.get(
                "total_fees",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            status = request.form.get(
                "status",
                "Active"
            ).strip()


            # =========================
            # VALIDATION
            # =========================

            if not course_name or not course_code:

                cursor.close()
                conn.close()

                flash(
                    "Course name and course code are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_course",
                        id=id
                    )
                )


            # =========================
            # FEES VALIDATION
            # =========================

            if total_fees == "":
                total_fees = 0

            try:

                total_fees = float(
                    total_fees
                )

                if total_fees < 0:
                    raise ValueError

            except ValueError:

                cursor.close()
                conn.close()

                flash(
                    "Please enter a valid course fee.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_course",
                        id=id
                    )
                )


            # =========================
            # DUPLICATE COURSE CODE
            # =========================

            cursor.execute("""
                SELECT id
                FROM courses
                WHERE course_code = %s
                AND id != %s
            """, (
                course_code,
                id
            ))

            duplicate = cursor.fetchone()

            if duplicate:

                cursor.close()
                conn.close()

                flash(
                    "Course code already exists.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_course",
                        id=id
                    )
                )


            # =========================
            # UPDATE DATABASE
            # =========================

            cursor.execute("""
                UPDATE courses
                SET
                    course_name = %s,
                    course_code = %s,
                    duration = %s,
                    total_fees = %s,
                    description = %s,
                    status = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                course_name,
                course_code,
                duration or None,
                total_fees,
                description or None,
                status,
                id
            ))


            conn.commit()


            cursor.close()
            conn.close()


            flash(
                "Course updated successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "course_details",
                    id=id
                )
            )


        # =========================
        # GET FORM
        # =========================

        cursor.close()
        conn.close()

        return render_template(
            "edit_course.html",
            course=course
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

# =========================
# DELETE COURSE
# =========================

@app.route("/courses/<int:id>/delete", methods=["POST"])
def delete_course(id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM courses
            WHERE id = %s
        """, (id,))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Course deleted successfully.", "success")

        return redirect(url_for("courses"))

    except mysql.connector.Error as error:
        return f"Database Error: {error}", 500

# =========================
# STUDENT COURSE ENROLLMENT
# =========================

@app.route("/students/<int:student_id>/enroll", methods=["GET", "POST"])
def enroll_student(student_id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Student
        cursor.execute("""
            SELECT *
            FROM students
            WHERE id = %s
        """, (student_id,))

        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return "Student not found", 404

        # Available courses
        cursor.execute("""
            SELECT *
            FROM courses
            WHERE status = 'Active'
            ORDER BY course_name ASC
        """)

        courses = cursor.fetchall()

        if request.method == "POST":

            course_id = request.form.get("course_id")
            enrollment_date = request.form.get("enrollment_date") or None
            status = request.form.get("status", "Active")

            if not course_id:
                flash("Please select a course.", "danger")

                cursor.close()
                conn.close()

                return redirect(
                    url_for("enroll_student", student_id=student_id)
                )

            # Check existing enrollment
            cursor.execute("""
                SELECT id
                FROM student_courses
                WHERE student_id = %s
                AND course_id = %s
            """, (student_id, course_id))

            existing = cursor.fetchone()

            if existing:
                flash(
                    "Student is already enrolled in this course.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for("enroll_student", student_id=student_id)
                )

            # Insert enrollment
            cursor.execute("""
                INSERT INTO student_courses (
                    student_id,
                    course_id,
                    enrollment_date,
                    status
                )
                VALUES (%s, %s, %s, %s)
            """, (
                student_id,
                course_id,
                enrollment_date,
                status
            ))

            conn.commit()

            cursor.close()
            conn.close()

            flash(
                "Student enrolled in course successfully.",
                "success"
            )

            return redirect(
                url_for("student_details", id=student_id)
            )

        cursor.close()
        conn.close()

        return render_template(
            "enroll_student.html",
            student=student,
            courses=courses
        )

    except mysql.connector.Error as error:
        return f"Database Error: {error}", 500    

# =========================
# ATTENDANCE ROUTES
# =========================

# =========================
# ATTENDANCE LIST
# =========================

@app.route("/attendance")
def attendance():

    selected_date = request.args.get(
        "date",
        ""
    ).strip()

    selected_status = request.args.get(
        "status",
        ""
    ).strip()


    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # =========================
        # BASE QUERY
        # =========================

        query = """
            SELECT
                a.id,
                a.student_id,
                a.attendance_date,
                a.status,
                a.remarks,
                s.admission_no,
                s.student_name
            FROM attendance a
            INNER JOIN students s
                ON s.id = a.student_id
            WHERE 1 = 1
        """

        params = []


        # =========================
        # DATE FILTER
        # =========================

        if selected_date:

            query += """
                AND a.attendance_date = %s
            """

            params.append(
                selected_date
            )


        # =========================
        # STATUS FILTER
        # =========================

        if selected_status:

            query += """
                AND a.status = %s
            """

            params.append(
                selected_status
            )


        # =========================
        # ORDER
        # =========================

        query += """
            ORDER BY
                a.attendance_date DESC,
                a.id DESC
        """


        cursor.execute(
            query,
            tuple(params)
        )

        attendance_records = cursor.fetchall()


        cursor.close()
        conn.close()


        return render_template(
            "attendance.html",
            attendance_records=attendance_records,
            selected_date=selected_date,
            selected_status=selected_status
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

# =========================
# MARK ATTENDANCE
# =========================

@app.route("/attendance/mark", methods=["GET", "POST"])
def mark_attendance():

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # GET ACTIVE STUDENTS
        # =========================

        cursor.execute("""
            SELECT
                id,
                admission_no,
                student_name
            FROM students
            WHERE status = 'Active'
            ORDER BY student_name ASC
        """)

        students = cursor.fetchall()


        # =========================
        # SAVE ATTENDANCE
        # =========================

        if request.method == "POST":

            attendance_date = request.form.get(
                "attendance_date",
                ""
            ).strip()


            # =========================
            # DATE VALIDATION
            # =========================

            if not attendance_date:

                cursor.close()
                conn.close()

                flash(
                    "Attendance date is required.",
                    "danger"
                )

                return redirect(
                    url_for("mark_attendance")
                )


            # =========================
            # PROCESS EACH STUDENT
            # =========================

            for student in students:

                student_id = student["id"]

                status = request.form.get(
                    f"status_{student_id}",
                    "Present"
                ).strip()

                remarks = request.form.get(
                    f"remarks_{student_id}",
                    ""
                ).strip()


                # =========================
                # CHECK EXISTING RECORD
                # =========================

                cursor.execute("""
                    SELECT id
                    FROM attendance
                    WHERE student_id = %s
                    AND attendance_date = %s
                """, (
                    student_id,
                    attendance_date
                ))

                existing_record = cursor.fetchone()


                # =========================
                # UPDATE EXISTING
                # =========================

                if existing_record:

                    cursor.execute("""
                        UPDATE attendance
                        SET
                            status = %s,
                            remarks = %s
                        WHERE id = %s
                    """, (
                        status,
                        remarks or None,
                        existing_record["id"]
                    ))


                # =========================
                # INSERT NEW
                # =========================

                else:

                    cursor.execute("""
                        INSERT INTO attendance (
                            student_id,
                            attendance_date,
                            status,
                            remarks,
                            created_at
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            NOW()
                        )
                    """, (
                        student_id,
                        attendance_date,
                        status,
                        remarks or None
                    ))


            conn.commit()


            cursor.close()
            conn.close()


            flash(
                "Attendance saved successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "attendance",
                    date=attendance_date
                )
            )


        # =========================
        # GET PAGE
        # =========================

        cursor.close()
        conn.close()

        return render_template(
            "mark_attendance.html",
            students=students,
            selected_date=""
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )
    # =========================
# EDIT ATTENDANCE
# =========================

@app.route("/attendance/edit/<int:id>", methods=["GET", "POST"])
def edit_attendance(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get attendance record
        cursor.execute("""
            SELECT
                a.id,
                a.student_id,
                a.attendance_date,
                a.status,
                a.remarks,
                s.student_name,
                s.admission_no
            FROM attendance a
            INNER JOIN students s
                ON s.id = a.student_id
            WHERE a.id = %s
        """, (id,))

        attendance_record = cursor.fetchone()

        if not attendance_record:

            cursor.close()
            conn.close()

            flash(
                "Attendance record not found.",
                "danger"
            )

            return redirect(
                url_for("attendance")
            )


        # =========================
        # UPDATE
        # =========================

        if request.method == "POST":

            attendance_date = (
                request.form.get(
                    "attendance_date"
                ) or None
            )

            status = request.form.get(
                "status",
                ""
            ).strip()

            remarks = request.form.get(
                "remarks",
                ""
            ).strip()


            if not attendance_date or not status:

                cursor.close()
                conn.close()

                flash(
                    "Date and status are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_attendance",
                        id=id
                    )
                )


            cursor.execute("""
                UPDATE attendance
                SET
                    attendance_date = %s,
                    status = %s,
                    remarks = %s
                WHERE id = %s
            """, (
                attendance_date,
                status,
                remarks or None,
                id
            ))


            conn.commit()

            cursor.close()
            conn.close()


            flash(
                "Attendance updated successfully.",
                "success"
            )

            return redirect(
                url_for("attendance")
            )


        cursor.close()
        conn.close()

        return render_template(
            "edit_attendance.html",
            attendance=attendance_record
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

# =========================
# ATTENDANCE REPORT
# =========================

@app.route("/attendance/report")
def attendance_report():

    from_date = request.args.get(
        "from_date",
        ""
    ).strip()

    to_date = request.args.get(
        "to_date",
        ""
    ).strip()

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                s.id,
                s.admission_no,
                s.student_name,

                COUNT(a.id) AS total_days,

                SUM(
                    CASE
                        WHEN a.status = 'Present'
                        THEN 1
                        ELSE 0
                    END
                ) AS present_days,

                SUM(
                    CASE
                        WHEN a.status = 'Absent'
                        THEN 1
                        ELSE 0
                    END
                ) AS absent_days,

                SUM(
                    CASE
                        WHEN a.status = 'Leave'
                        THEN 1
                        ELSE 0
                    END
                ) AS leave_days

            FROM students s

            LEFT JOIN attendance a
                ON a.student_id = s.id
        """

        conditions = [
            "s.status = 'Active'"
        ]

        params = []


        # =========================
        # FROM DATE
        # =========================

        if from_date:

            conditions.append("""
                a.attendance_date >= %s
            """)

            params.append(
                from_date
            )


        # =========================
        # TO DATE
        # =========================

        if to_date:

            conditions.append("""
                a.attendance_date <= %s
            """)

            params.append(
                to_date
            )


        # =========================
        # WHERE
        # =========================

        query += """
            WHERE
        """ + " AND ".join(conditions)


        # =========================
        # GROUP
        # =========================

        query += """
            GROUP BY
                s.id,
                s.admission_no,
                s.student_name

            ORDER BY
                s.student_name ASC
        """


        cursor.execute(
            query,
            tuple(params)
        )

        attendance_report_data = cursor.fetchall()


        # =========================
        # PERCENTAGE
        # =========================

        for record in attendance_report_data:

            total_days = (
                record["total_days"] or 0
            )

            present_days = (
                record["present_days"] or 0
            )


            if total_days > 0:

                record[
                    "attendance_percentage"
                ] = round(
                    (
                        present_days
                        / total_days
                    ) * 100,
                    2
                )

            else:

                record[
                    "attendance_percentage"
                ] = 0


        cursor.close()
        conn.close()


        return render_template(
            "attendance_report.html",

            attendance_report=attendance_report_data,

            from_date=from_date,

            to_date=to_date
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

@app.route("/attendance/student/<int:id>")
def student_attendance(id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                admission_no,
                student_name
            FROM students
            WHERE id = %s
        """, (id,))

        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return "Student not found", 404

        cursor.execute("""
            SELECT
                attendance_date,
                status,
                remarks
            FROM attendance
            WHERE student_id = %s
            ORDER BY attendance_date DESC
        """, (id,))

        attendance_records = cursor.fetchall()

        cursor.close()
        conn.close()

        total_days = len(attendance_records)

        present_days = sum(
            1 for record in attendance_records
            if record["status"] == "Present"
        )

        absent_days = sum(
            1 for record in attendance_records
            if record["status"] == "Absent"
        )

        leave_days = sum(
            1 for record in attendance_records
            if record["status"] == "Leave"
        )

        attendance_percentage = (
            round((present_days / total_days) * 100, 2)
            if total_days > 0
            else 0
        )

        return render_template(
            "student_attendance.html",
            student=student,
            attendance_records=attendance_records,
            total_days=total_days,
            present_days=present_days,
            absent_days=absent_days,
            leave_days=leave_days,
            attendance_percentage=attendance_percentage
        )

    except Exception as error:
        return f"<h2>Attendance Error</h2><pre>{error}</pre>", 500

# =========================
# FEE PAYMENTS LIST
# =========================

# =========================
# FEES
# =========================

@app.route("/fees")
def fees():

    search = request.args.get(
        "search",
        ""
    ).strip()

    payment_mode = request.args.get(
        "payment_mode",
        ""
    ).strip()


    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # =========================
        # PAYMENT RECORDS
        # =========================

        query = """
            SELECT
                fp.id,
                fp.receipt_no,
                fp.student_id,
                fp.course_id,
                fp.amount,
                fp.payment_date,
                fp.payment_mode,
                fp.remarks,
                fp.created_at,

                s.student_name,
                s.admission_no,

                c.course_name,
                c.course_code,
                c.total_fees

            FROM fee_payments fp

            INNER JOIN students s
                ON s.id = fp.student_id

            LEFT JOIN courses c
                ON c.id = fp.course_id

            WHERE 1 = 1
        """

        params = []


        # =========================
        # SEARCH
        # =========================

        if search:

            query += """
                AND (
                    fp.receipt_no LIKE %s
                    OR s.student_name LIKE %s
                    OR s.admission_no LIKE %s
                )
            """

            search_value = f"%{search}%"

            params.extend([
                search_value,
                search_value,
                search_value
            ])


        # =========================
        # PAYMENT MODE
        # =========================

        if payment_mode:

            query += """
                AND fp.payment_mode = %s
            """

            params.append(
                payment_mode
            )


        # =========================
        # ORDER
        # =========================

        query += """
            ORDER BY
                fp.payment_date DESC,
                fp.id DESC
        """


        cursor.execute(
            query,
            tuple(params)
        )

        payments = cursor.fetchall()


        # =========================
        # CALCULATE PAID / REMAINING
        # COURSE-WISE
        # =========================

        for payment in payments:

            if payment["course_id"]:

                cursor.execute("""
                    SELECT
                        COALESCE(
                            SUM(amount),
                            0
                        ) AS paid_amount

                    FROM fee_payments

                    WHERE student_id = %s
                    AND course_id = %s
                """, (
                    payment["student_id"],
                    payment["course_id"]
                ))

                paid_data = cursor.fetchone()

                paid_amount = (
                    paid_data["paid_amount"]
                    or 0
                )

                total_fees = (
                    payment["total_fees"]
                    or 0
                )

                remaining_fees = (
                    total_fees
                    - paid_amount
                )

                if remaining_fees < 0:
                    remaining_fees = 0

                payment["paid_fees"] = paid_amount

                payment["remaining_fees"] = remaining_fees

            else:

                payment["paid_fees"] = None

                payment["remaining_fees"] = None


        # =========================
        # TOTAL SUMMARY
        # =========================

        cursor.execute("""
            SELECT
                COALESCE(
                    SUM(amount),
                    0
                ) AS total_collected

            FROM fee_payments
        """)

        summary_data = cursor.fetchone()

        total_collected = (
            summary_data["total_collected"]
            or 0
        )


        # =========================
        # TOTAL FEES FROM
        # ASSIGNED COURSES
        # =========================

        cursor.execute("""
            SELECT
                COALESCE(
                    SUM(c.total_fees),
                    0
                ) AS total_fees

            FROM student_courses sc

            INNER JOIN courses c
                ON c.id = sc.course_id

            WHERE sc.status != 'Dropped'
        """)

        total_fee_data = cursor.fetchone()

        total_fees = (
            total_fee_data["total_fees"]
            or 0
        )


        # =========================
        # TOTAL REMAINING
        # =========================

        total_remaining = (
            total_fees
            - total_collected
        )

        if total_remaining < 0:
            total_remaining = 0


        cursor.close()
        conn.close()


        return render_template(
            "fees.html",

            payments=payments,

            search=search,

            payment_mode=payment_mode,

            total_fees=total_fees,

            total_collected=total_collected,

            total_remaining=total_remaining
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

@app.route("/fees/add", methods=["GET", "POST"])
def add_fee():

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Active students
        cursor.execute("""
            SELECT
                id,
                admission_no,
                student_name
            FROM students
            WHERE status = 'Active'
            ORDER BY student_name ASC
        """)

        students = cursor.fetchall()

        # Active courses
        cursor.execute("""
            SELECT
                id,
                course_code,
                course_name
            FROM courses
            WHERE status = 'Active'
            ORDER BY course_name ASC
        """)

        courses = cursor.fetchall()

        if request.method == "POST":

            receipt_no = request.form.get("receipt_no", "").strip()
            student_id = request.form.get("student_id")
            course_id = request.form.get("course_id") or None
            amount = request.form.get("amount", "0").strip()
            payment_date = request.form.get("payment_date")
            payment_mode = request.form.get(
                "payment_mode",
                "Cash"
            )
            remarks = request.form.get(
                "remarks",
                ""
            ).strip()

            if not receipt_no or not student_id or not amount or not payment_date:

                flash(
                    "Receipt No., Student, Amount and Payment Date are required.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(url_for("add_fee"))

            try:

                cursor.execute("""
                    INSERT INTO fee_payments (
                        receipt_no,
                        student_id,
                        course_id,
                        amount,
                        payment_date,
                        payment_mode,
                        remarks
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    receipt_no,
                    student_id,
                    course_id,
                    amount,
                    payment_date,
                    payment_mode,
                    remarks
                ))

                conn.commit()

                cursor.close()
                conn.close()

                flash(
                    "Fee payment added successfully.",
                    "success"
                )

                return redirect(
                    url_for("fees")
                )

            except mysql.connector.IntegrityError:

                flash(
                    "Receipt number already exists.",
                    "danger"
                )

        cursor.close()
        conn.close()

        return render_template(
            "add_fee.html",
            students=students,
            courses=courses
        )

    except mysql.connector.Error as error:

        return f"Database Error: {error}", 500

# =========================
# FEE DETAILS
# =========================

@app.route("/fees/<int:id>")
def fee_details(id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                fp.*,
                s.admission_no,
                s.student_name,
                s.father_name,
                s.mobile,
                s.email,
                c.course_code,
                c.course_name,
                c.total_fees
            FROM fee_payments fp

            INNER JOIN students s
                ON s.id = fp.student_id

            LEFT JOIN courses c
                ON c.id = fp.course_id

            WHERE fp.id = %s
        """, (id,))

        payment = cursor.fetchone()

        if not payment:
            cursor.close()
            conn.close()
            return "Fee payment not found", 404

        # Total paid by student for selected course
        if payment["course_id"]:

            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) AS total_paid
                FROM fee_payments
                WHERE student_id = %s
                AND course_id = %s
            """, (
                payment["student_id"],
                payment["course_id"]
            ))

        else:

            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) AS total_paid
                FROM fee_payments
                WHERE student_id = %s
            """, (
                payment["student_id"],
            ))

        total_paid = cursor.fetchone()["total_paid"] or 0

        course_fees = payment["total_fees"] or 0

        remaining_amount = max(
            float(course_fees) - float(total_paid),
            0
        )

        cursor.close()
        conn.close()

        return render_template(
            "fee_details.html",
            payment=payment,
            total_paid=total_paid,
            remaining_amount=remaining_amount
        )

    except mysql.connector.Error as error:

        return f"Database Error: {error}", 500

# =========================
# FEE RECEIPT
# =========================

@app.route("/fees/receipt/<int:id>")
def fee_receipt(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                fp.id,
                fp.receipt_no,
                fp.student_id,
                fp.course_id,
                fp.amount,
                fp.payment_date,
                fp.payment_mode,
                fp.remarks,
                fp.created_at,

                s.student_name,
                s.admission_no,

                c.course_name

            FROM fee_payments fp

            INNER JOIN students s
                ON s.id = fp.student_id

            LEFT JOIN courses c
                ON c.id = fp.course_id

            WHERE fp.id = %s
        """, (id,))

        payment = cursor.fetchone()

        cursor.close()
        conn.close()

        if not payment:

            flash(
                "Fee payment not found.",
                "danger"
            )

            return redirect(
                url_for("fees")
            )

        return render_template(
            "fee_receipt.html",
            payment=payment
        )

    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

# =========================
# EDIT FEE PAYMENT
# =========================

@app.route("/fees/edit/<int:id>", methods=["GET", "POST"])
def edit_fee(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # GET PAYMENT
        # =========================

        cursor.execute("""
            SELECT
                fp.id,
                fp.receipt_no,
                fp.student_id,
                fp.course_id,
                fp.amount,
                fp.payment_date,
                fp.payment_mode,
                fp.remarks,
                fp.created_at,

                s.student_name,
                s.admission_no,

                c.course_name

            FROM fee_payments fp

            INNER JOIN students s
                ON s.id = fp.student_id

            LEFT JOIN courses c
                ON c.id = fp.course_id

            WHERE fp.id = %s
        """, (id,))

        payment = cursor.fetchone()

        if not payment:

            cursor.close()
            conn.close()

            flash(
                "Fee payment not found.",
                "danger"
            )

            return redirect(
                url_for("fees")
            )


        # =========================
        # UPDATE
        # =========================

        if request.method == "POST":

            amount = request.form.get(
                "amount",
                ""
            ).strip()

            payment_date = request.form.get(
                "payment_date",
                ""
            ).strip()

            payment_mode = request.form.get(
                "payment_mode",
                ""
            ).strip()

            remarks = request.form.get(
                "remarks",
                ""
            ).strip()


            # =========================
            # VALIDATION
            # =========================

            if not amount or not payment_date:

                cursor.close()
                conn.close()

                flash(
                    "Amount and payment date are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_fee",
                        id=id
                    )
                )


            try:

                amount = float(amount)

                if amount <= 0:
                    raise ValueError

            except ValueError:

                cursor.close()
                conn.close()

                flash(
                    "Please enter a valid payment amount.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_fee",
                        id=id
                    )
                )


            # =========================
            # UPDATE DATABASE
            # =========================

            cursor.execute("""
                UPDATE fee_payments
                SET
                    amount = %s,
                    payment_date = %s,
                    payment_mode = %s,
                    remarks = %s
                WHERE id = %s
            """, (
                amount,
                payment_date,
                payment_mode or None,
                remarks or None,
                id
            ))


            conn.commit()

            cursor.close()
            conn.close()


            flash(
                "Fee payment updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "fee_details",
                    id=id
                )
            )


        # =========================
        # GET FORM
        # =========================

        cursor.close()
        conn.close()

        return render_template(
            "edit_fee.html",
            payment=payment
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# EXAMS LIST
# =========================

@app.route("/exams")
def exams():

    search = request.args.get(
        "search",
        ""
    ).strip()

    status = request.args.get(
        "status",
        ""
    ).strip()


    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # =========================
        # BASE QUERY
        # =========================

        query = """
            SELECT
                id,
                exam_name,
                exam_date,
                description,
                status,
                created_at

            FROM exams

            WHERE 1 = 1
        """

        params = []


        # =========================
        # SEARCH
        # =========================

        if search:

            query += """
                AND exam_name LIKE %s
            """

            params.append(
                f"%{search}%"
            )


        # =========================
        # STATUS FILTER
        # =========================

        if status:

            query += """
                AND status = %s
            """

            params.append(
                status
            )


        # =========================
        # ORDER
        # =========================

        query += """
            ORDER BY
                exam_date DESC,
                id DESC
        """


        cursor.execute(
            query,
            tuple(params)
        )

        exams_data = cursor.fetchall()


        cursor.close()
        conn.close()


        return render_template(
            "exams.html",
            exams=exams_data,
            search=search,
            status=status
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# ADD EXAM
# =========================

@app.route("/exams/add", methods=["GET", "POST"])
def add_exam():

    if request.method == "POST":

        exam_name = request.form.get(
            "exam_name",
            ""
        ).strip()

        exam_date = request.form.get(
            "exam_date",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "Active"
        ).strip()


        # =========================
        # VALIDATION
        # =========================

        if not exam_name or not exam_date:

            flash(
                "Exam name and exam date are required.",
                "danger"
            )

            return redirect(
                url_for("add_exam")
            )


        try:

            conn = get_db_connection()
            cursor = conn.cursor()


            cursor.execute("""
                INSERT INTO exams (
                    exam_name,
                    exam_date,
                    description,
                    status,
                    created_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )
            """, (
                exam_name,
                exam_date,
                description or None,
                status,
            ))


            conn.commit()

            cursor.close()
            conn.close()


            flash(
                "Exam added successfully.",
                "success"
            )

            return redirect(
                url_for("exams")
            )


        except mysql.connector.Error as error:

            return (
                f"Database Error: {error}",
                500
            )


    return render_template(
        "add_exam.html"
    )

# =========================
# EDIT EXAM
# =========================

@app.route("/exams/edit/<int:id>", methods=["GET", "POST"])
def edit_exam(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # =========================
        # GET EXAM
        # =========================

        cursor.execute("""
            SELECT
                id,
                exam_name,
                exam_date,
                description,
                status,
                created_at
            FROM exams
            WHERE id = %s
        """, (id,))

        exam = cursor.fetchone()


        if not exam:

            cursor.close()
            conn.close()

            flash(
                "Exam not found.",
                "danger"
            )

            return redirect(
                url_for("exams")
            )


        # =========================
        # UPDATE
        # =========================

        if request.method == "POST":

            exam_name = request.form.get(
                "exam_name",
                ""
            ).strip()

            exam_date = request.form.get(
                "exam_date",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            status = request.form.get(
                "status",
                "Active"
            ).strip()


            if not exam_name or not exam_date:

                cursor.close()
                conn.close()

                flash(
                    "Exam name and exam date are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "edit_exam",
                        id=id
                    )
                )


            cursor.execute("""
                UPDATE exams
                SET
                    exam_name = %s,
                    exam_date = %s,
                    description = %s,
                    status = %s
                WHERE id = %s
            """, (
                exam_name,
                exam_date,
                description or None,
                status,
                id
            ))


            conn.commit()

            cursor.close()
            conn.close()


            flash(
                "Exam updated successfully.",
                "success"
            )

            return redirect(
                url_for("exams")
            )


        # =========================
        # SHOW FORM
        # =========================

        cursor.close()
        conn.close()

        return render_template(
            "edit_exam.html",
            exam=exam
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# EXAM DETAILS
# =========================

@app.route("/exams/details/<int:id>")
def exam_details(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                exam_name,
                exam_date,
                description,
                status,
                created_at
            FROM exams
            WHERE id = %s
        """, (id,))

        exam = cursor.fetchone()

        cursor.close()
        conn.close()

        if not exam:

            flash(
                "Exam not found.",
                "danger"
            )

            return redirect(
                url_for("exams")
            )

        return render_template(
            "exam_details.html",
            exam=exam
        )

    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# EXAM SCHEDULE LIST
# =========================

@app.route("/exam-schedule")
def exam_schedule():

    exam_id = request.args.get(
        "exam_id",
        ""
    ).strip()

    subject = request.args.get(
        "subject",
        ""
    ).strip()

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # EXAMS FOR DROPDOWN
        # =========================

        cursor.execute("""
            SELECT
                id,
                exam_name
            FROM exams
            WHERE status != 'Cancelled'
            ORDER BY exam_date DESC, id DESC
        """)

        exams_data = cursor.fetchall()


        # =========================
        # SCHEDULE QUERY
        # =========================

        query = """
            SELECT
                es.id,
                es.exam_id,
                es.subject_name,
                es.exam_date,
                es.start_time,
                es.end_time,
                es.room_no,
                es.description,

                e.exam_name

            FROM exam_schedule es

            INNER JOIN exams e
                ON e.id = es.exam_id

            WHERE 1 = 1
        """

        params = []


        # =========================
        # EXAM FILTER
        # =========================

        if exam_id:

            query += """
                AND es.exam_id = %s
            """

            params.append(
                exam_id
            )


        # =========================
        # SUBJECT FILTER
        # =========================

        if subject:

            query += """
                AND es.subject_name LIKE %s
            """

            params.append(
                f"%{subject}%"
            )


        # =========================
        # ORDER
        # =========================

        query += """
            ORDER BY
                es.exam_date ASC,
                es.start_time ASC,
                es.id DESC
        """


        cursor.execute(
            query,
            tuple(params)
        )

        schedules = cursor.fetchall()


        cursor.close()
        conn.close()


        return render_template(
            "exam_schedule.html",

            schedules=schedules,

            exams=exams_data,

            exam_id=exam_id,

            subject=subject
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )
    # =========================
# ADD EXAM SCHEDULE
# =========================

@app.route("/exam-schedule/add", methods=["GET", "POST"])
def add_exam_schedule():

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # =========================
        # EXAMS DROPDOWN
        # =========================

        cursor.execute("""
            SELECT
                id,
                exam_name
            FROM exams
            WHERE status != 'Cancelled'
            ORDER BY exam_date DESC, id DESC
        """)

        exams_data = cursor.fetchall()


        # =========================
        # SAVE
        # =========================

        if request.method == "POST":

            exam_id = request.form.get(
                "exam_id",
                ""
            ).strip()

            subject_name = request.form.get(
                "subject_name",
                ""
            ).strip()

            exam_date = request.form.get(
                "exam_date",
                ""
            ).strip()

            start_time = request.form.get(
                "start_time",
                ""
            ).strip()

            end_time = request.form.get(
                "end_time",
                ""
            ).strip()

            room_no = request.form.get(
                "room_no",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()


            # =========================
            # VALIDATION
            # =========================

            if (
                not exam_id
                or not subject_name
                or not exam_date
                or not start_time
                or not end_time
            ):

                cursor.close()
                conn.close()

                flash(
                    "Please fill all required fields.",
                    "danger"
                )

                return redirect(
                    url_for("add_exam_schedule")
                )


            # =========================
            # INSERT
            # =========================

            cursor.execute("""
                INSERT INTO exam_schedule (
                    exam_id,
                    subject_name,
                    exam_date,
                    start_time,
                    end_time,
                    room_no,
                    description,
                    created_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )
            """, (
                exam_id,
                subject_name,
                exam_date,
                start_time,
                end_time,
                room_no or None,
                description or None
            ))


            conn.commit()

            cursor.close()
            conn.close()


            flash(
                "Exam schedule added successfully.",
                "success"
            )

            return redirect(
                url_for("exam_schedule")
            )


        cursor.close()
        conn.close()


        return render_template(
            "add_exam_schedule.html",
            exams=exams_data
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# EXAM SCHEDULE DETAILS
# =========================

@app.route("/exam-schedule/details/<int:id>")
def exam_schedule_details(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                es.id,
                es.exam_id,
                es.subject_name,
                es.exam_date,
                es.start_time,
                es.end_time,
                es.room_no,
                es.description,
                es.created_at,

                e.exam_name

            FROM exam_schedule es

            INNER JOIN exams e
                ON e.id = es.exam_id

            WHERE es.id = %s
        """, (id,))

        schedule = cursor.fetchone()

        cursor.close()
        conn.close()

        if not schedule:

            flash(
                "Exam schedule not found.",
                "danger"
            )

            return redirect(
                url_for("exam_schedule")
            )

        return render_template(
            "exam_schedule_details.html",
            schedule=schedule
        )

    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# EDIT EXAM SCHEDULE
# =========================

@app.route("/exam-schedule/edit/<int:id>", methods=["GET", "POST"])
def edit_exam_schedule(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # GET SCHEDULE
        # =========================

        cursor.execute("""
            SELECT
                id,
                exam_id,
                subject_name,
                exam_date,
                start_time,
                end_time,
                room_no,
                description,
                created_at
            FROM exam_schedule
            WHERE id = %s
        """, (id,))

        schedule = cursor.fetchone()

        if not schedule:

            cursor.close()
            conn.close()

            flash(
                "Exam schedule not found.",
                "danger"
            )

            return redirect(
                url_for("exam_schedule")
            )

        # =========================
        # EXAMS DROPDOWN
        # =========================

        cursor.execute("""
            SELECT
                id,
                exam_name
            FROM exams
            WHERE status != 'Cancelled'
            ORDER BY exam_date DESC, id DESC
        """)

        exams_data = cursor.fetchall()

        # =========================
        # UPDATE
        # =========================

        if request.method == "POST":

            exam_id = request.form.get(
                "exam_id",
                ""
            ).strip()

            subject_name = request.form.get(
                "subject_name",
                ""
            ).strip()

            exam_date = request.form.get(
                "exam_date",
                ""
            ).strip()

            start_time = request.form.get(
                "start_time",
                ""
            ).strip()

            end_time = request.form.get(
                "end_time",
                ""
            ).strip()

            room_no = request.form.get(
                "room_no",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            # =========================
            # VALIDATION
            # =========================

            if (
                not exam_id
                or not subject_name
                or not exam_date
                or not start_time
                or not end_time
            ):

                flash(
                    "Please fill all required fields.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for(
                        "edit_exam_schedule",
                        id=id
                    )
                )

            # =========================
            # UPDATE DATABASE
            # =========================

            cursor.execute("""
                UPDATE exam_schedule
                SET
                    exam_id = %s,
                    subject_name = %s,
                    exam_date = %s,
                    start_time = %s,
                    end_time = %s,
                    room_no = %s,
                    description = %s
                WHERE id = %s
            """, (
                exam_id,
                subject_name,
                exam_date,
                start_time,
                end_time,
                room_no or None,
                description or None,
                id
            ))

            conn.commit()

            cursor.close()
            conn.close()

            flash(
                "Exam schedule updated successfully.",
                "success"
            )

            return redirect(
                url_for("exam_schedule")
            )

        # =========================
        # SHOW FORM
        # =========================

        cursor.close()
        conn.close()

        return render_template(
            "edit_exam_schedule.html",
            schedule=schedule,
            exams=exams_data
        )

    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# RESULTS LIST
# =========================

@app.route("/results")
def results():

    student_id = request.args.get(
        "student_id",
        ""
    ).strip()

    exam_id = request.args.get(
        "exam_id",
        ""
    ).strip()

    subject = request.args.get(
        "subject",
        ""
    ).strip()

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # STUDENTS DROPDOWN
        # =========================

        cursor.execute("""
            SELECT
                id,
                student_name,
                admission_no
            FROM students
            ORDER BY student_name ASC
        """)

        students_data = cursor.fetchall()


        # =========================
        # EXAMS DROPDOWN
        # =========================

        cursor.execute("""
            SELECT
                id,
                exam_name
            FROM exams
            ORDER BY exam_date DESC, id DESC
        """)

        exams_data = cursor.fetchall()


        # =========================
        # RESULTS QUERY
        # =========================

        query = """
            SELECT
                r.id,
                r.student_id,
                r.exam_id,
                r.subject,
                r.marks,
                r.max_marks,
                r.grade,
                r.remarks,
                r.created_at,

                s.student_name,
                s.admission_no,

                e.exam_name

            FROM results r

            INNER JOIN students s
                ON s.id = r.student_id

            INNER JOIN exams e
                ON e.id = r.exam_id

            WHERE 1 = 1
        """

        params = []


        # =========================
        # STUDENT FILTER
        # =========================

        if student_id:

            query += """
                AND r.student_id = %s
            """

            params.append(
                student_id
            )


        # =========================
        # EXAM FILTER
        # =========================

        if exam_id:

            query += """
                AND r.exam_id = %s
            """

            params.append(
                exam_id
            )


        # =========================
        # SUBJECT SEARCH
        # =========================

        if subject:

            query += """
                AND r.subject LIKE %s
            """

            params.append(
                f"%{subject}%"
            )


        # =========================
        # ORDER
        # =========================

        query += """
            ORDER BY
                r.created_at DESC,
                r.id DESC
        """


        cursor.execute(
            query,
            tuple(params)
        )

        results_data = cursor.fetchall()


        cursor.close()
        conn.close()


        return render_template(
            "results.html",

            results=results_data,

            students=students_data,

            exams=exams_data,

            student_id=student_id,

            exam_id=exam_id,

            subject=subject
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# ADD RESULT
# =========================

@app.route("/results/add", methods=["GET", "POST"])
def add_result():

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # =========================
        # STUDENTS
        # =========================

        cursor.execute("""
            SELECT
                id,
                student_name,
                admission_no
            FROM students
            ORDER BY student_name ASC
        """)

        students_data = cursor.fetchall()


        # =========================
        # EXAMS
        # =========================

        cursor.execute("""
            SELECT
                id,
                exam_name
            FROM exams
            WHERE status != 'Cancelled'
            ORDER BY exam_date DESC, id DESC
        """)

        exams_data = cursor.fetchall()


        # =========================
        # SAVE RESULT
        # =========================

        if request.method == "POST":

            student_id = request.form.get(
                "student_id",
                ""
            ).strip()

            exam_id = request.form.get(
                "exam_id",
                ""
            ).strip()

            subject = request.form.get(
                "subject",
                ""
            ).strip()

            marks = request.form.get(
                "marks",
                ""
            ).strip()

            max_marks = request.form.get(
                "max_marks",
                "100"
            ).strip()

            grade = request.form.get(
                "grade",
                ""
            ).strip()

            remarks = request.form.get(
                "remarks",
                ""
            ).strip()


            # =========================
            # VALIDATION
            # =========================

            if (
                not student_id
                or not exam_id
                or not subject
                or not marks
                or not max_marks
            ):

                flash(
                    "Please fill all required fields.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for("add_result")
                )


            try:

                marks_value = float(marks)
                max_marks_value = float(max_marks)

            except ValueError:

                flash(
                    "Marks must be a valid number.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for("add_result")
                )


            if max_marks_value <= 0:

                flash(
                    "Maximum marks must be greater than zero.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for("add_result")
                )


            if marks_value < 0 or marks_value > max_marks_value:

                flash(
                    "Marks must be between 0 and maximum marks.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for("add_result")
                )


            # =========================
            # INSERT
            # =========================

            cursor.execute("""
                INSERT INTO results (
                    student_id,
                    exam_id,
                    subject,
                    marks,
                    max_marks,
                    grade,
                    remarks,
                    created_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )
            """, (
                student_id,
                exam_id,
                subject,
                marks_value,
                max_marks_value,
                grade or None,
                remarks or None
            ))


            conn.commit()

            cursor.close()
            conn.close()


            flash(
                "Result added successfully.",
                "success"
            )

            return redirect(
                url_for("results")
            )


        cursor.close()
        conn.close()


        return render_template(
            "add_result.html",
            students=students_data,
            exams=exams_data
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )
    # =========================
# RESULT DETAILS
# =========================

@app.route("/results/details/<int:id>")
def result_details(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                r.id,
                r.student_id,
                r.exam_id,
                r.subject,
                r.marks,
                r.max_marks,
                r.grade,
                r.remarks,
                r.created_at,

                s.student_name,
                s.admission_no,

                e.exam_name

            FROM results r

            INNER JOIN students s
                ON s.id = r.student_id

            INNER JOIN exams e
                ON e.id = r.exam_id

            WHERE r.id = %s
        """, (id,))

        result = cursor.fetchone()

        cursor.close()
        conn.close()


        if not result:

            flash(
                "Result not found.",
                "danger"
            )

            return redirect(
                url_for("results")
            )


        return render_template(
            "result_details.html",
            result=result
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )
    # =========================
# EDIT RESULT
# =========================

@app.route("/results/edit/<int:id>", methods=["GET", "POST"])
def edit_result(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # =========================
        # GET RESULT
        # =========================

        cursor.execute("""
            SELECT
                id,
                student_id,
                exam_id,
                subject,
                marks,
                max_marks,
                grade,
                remarks,
                created_at
            FROM results
            WHERE id = %s
        """, (id,))

        result = cursor.fetchone()


        if not result:

            cursor.close()
            conn.close()

            flash(
                "Result not found.",
                "danger"
            )

            return redirect(
                url_for("results")
            )


        # =========================
        # STUDENTS
        # =========================

        cursor.execute("""
            SELECT
                id,
                student_name,
                admission_no
            FROM students
            ORDER BY student_name ASC
        """)

        students_data = cursor.fetchall()


        # =========================
        # EXAMS
        # =========================

        cursor.execute("""
            SELECT
                id,
                exam_name
            FROM exams
            WHERE status != 'Cancelled'
            ORDER BY exam_date DESC, id DESC
        """)

        exams_data = cursor.fetchall()


        # =========================
        # UPDATE
        # =========================

        if request.method == "POST":

            student_id = request.form.get(
                "student_id",
                ""
            ).strip()

            exam_id = request.form.get(
                "exam_id",
                ""
            ).strip()

            subject = request.form.get(
                "subject",
                ""
            ).strip()

            marks = request.form.get(
                "marks",
                ""
            ).strip()

            max_marks = request.form.get(
                "max_marks",
                ""
            ).strip()

            grade = request.form.get(
                "grade",
                ""
            ).strip()

            remarks = request.form.get(
                "remarks",
                ""
            ).strip()


            # =========================
            # VALIDATION
            # =========================

            if (
                not student_id
                or not exam_id
                or not subject
                or not marks
                or not max_marks
            ):

                flash(
                    "Please fill all required fields.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for(
                        "edit_result",
                        id=id
                    )
                )


            try:

                marks_value = float(marks)
                max_marks_value = float(max_marks)

            except ValueError:

                flash(
                    "Marks must be a valid number.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for(
                        "edit_result",
                        id=id
                    )
                )


            if max_marks_value <= 0:

                flash(
                    "Maximum marks must be greater than zero.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for(
                        "edit_result",
                        id=id
                    )
                )


            if (
                marks_value < 0
                or marks_value > max_marks_value
            ):

                flash(
                    "Marks must be between 0 and maximum marks.",
                    "danger"
                )

                cursor.close()
                conn.close()

                return redirect(
                    url_for(
                        "edit_result",
                        id=id
                    )
                )


            # =========================
            # UPDATE DATABASE
            # =========================

            cursor.execute("""
                UPDATE results
                SET
                    student_id = %s,
                    exam_id = %s,
                    subject = %s,
                    marks = %s,
                    max_marks = %s,
                    grade = %s,
                    remarks = %s
                WHERE id = %s
            """, (
                student_id,
                exam_id,
                subject,
                marks_value,
                max_marks_value,
                grade or None,
                remarks or None,
                id
            ))


            conn.commit()

            cursor.close()
            conn.close()


            flash(
                "Result updated successfully.",
                "success"
            )

            return redirect(
                url_for("results")
            )


        cursor.close()
        conn.close()


        return render_template(
            "edit_result.html",
            result=result,
            students=students_data,
            exams=exams_data
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# DELETE RESULT
# =========================

@app.route("/results/delete/<int:id>", methods=["POST"])
def delete_result(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM results
            WHERE id = %s
        """, (id,))

        if cursor.rowcount == 0:

            cursor.close()
            conn.close()

            flash(
                "Result not found.",
                "danger"
            )

            return redirect(
                url_for("results")
            )

        conn.commit()

        cursor.close()
        conn.close()

        flash(
            "Result deleted successfully.",
            "success"
        )

        return redirect(
            url_for("results")
        )

    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )


    # =========================
# PROFILE
# =========================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    # Login check
    if "user_id" not in session:
        return redirect(url_for("login"))

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # =========================
        # GET CURRENT USER
        # =========================

        cursor.execute("""
            SELECT
                id,
                name,
                username,
                email,
                role,
                status,
                created_at,
                updated_at
            FROM users
            WHERE id = %s
        """, (session["user_id"],))

        user = cursor.fetchone()


        if not user:

            cursor.close()
            conn.close()

            session.clear()

            return redirect(
                url_for("login")
            )


        # =========================
        # POST
        # =========================

        if request.method == "POST":

            action = request.form.get(
                "action",
                ""
            ).strip()


            # =========================
            # UPDATE PROFILE
            # =========================

            if action == "profile":

                name = request.form.get(
                    "name",
                    ""
                ).strip()

                email = request.form.get(
                    "email",
                    ""
                ).strip()


                if not name or not email:

                    flash(
                        "Name and email are required.",
                        "danger"
                    )

                else:

                    # Check email already used
                    cursor.execute("""
                        SELECT id
                        FROM users
                        WHERE email = %s
                          AND id != %s
                    """, (
                        email,
                        session["user_id"]
                    ))

                    existing_email = cursor.fetchone()


                    if existing_email:

                        flash(
                            "Email address is already in use.",
                            "danger"
                        )

                    else:

                        cursor.execute("""
                            UPDATE users
                            SET
                                name = %s,
                                email = %s
                            WHERE id = %s
                        """, (
                            name,
                            email,
                            session["user_id"]
                        ))

                        conn.commit()

                        # Update session name
                        session["name"] = name

                        flash(
                            "Profile updated successfully.",
                            "success"
                        )


            # =========================
            # CHANGE PASSWORD
            # =========================

            elif action == "password":

                current_password = request.form.get(
                    "current_password",
                    ""
                )

                new_password = request.form.get(
                    "new_password",
                    ""
                )

                confirm_password = request.form.get(
                    "confirm_password",
                    ""
                )


                if not current_password:

                    flash(
                        "Current password is required.",
                        "danger"
                    )

                elif not new_password:

                    flash(
                        "New password is required.",
                        "danger"
                    )

                elif len(new_password) < 6:

                    flash(
                        "New password must be at least 6 characters.",
                        "danger"
                    )

                elif new_password != confirm_password:

                    flash(
                        "New password and confirm password do not match.",
                        "danger"
                    )

                else:

                    # Get password hash
                    cursor.execute("""
                        SELECT password
                        FROM users
                        WHERE id = %s
                    """, (
                        session["user_id"],
                    ))

                    password_data = cursor.fetchone()


                    if not password_data or not check_password_hash(
                        password_data["password"],
                        current_password
                    ):

                        flash(
                            "Current password is incorrect.",
                            "danger"
                        )

                    else:

                        new_password_hash = generate_password_hash(
                            new_password
                        )


                        cursor.execute("""
                            UPDATE users
                            SET
                                password = %s
                            WHERE id = %s
                        """, (
                            new_password_hash,
                            session["user_id"]
                        ))

                        conn.commit()

                        flash(
                            "Password changed successfully.",
                            "success"
                        )


        # Refresh user data
        cursor.execute("""
            SELECT
                id,
                name,
                username,
                email,
                role,
                status,
                created_at,
                updated_at
            FROM users
            WHERE id = %s
        """, (session["user_id"],))

        user = cursor.fetchone()


        cursor.close()
        conn.close()


        return render_template(
            "profile.html",
            user=user
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# ASSIGN COURSE TO STUDENT
# =========================

@app.route("/students/<int:id>/assign-course", methods=["GET", "POST"])
def assign_course(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # =========================
        # GET STUDENT
        # =========================

        cursor.execute("""
            SELECT
                id,
                admission_no,
                student_name
            FROM students
            WHERE id = %s
        """, (id,))

        student = cursor.fetchone()

        if not student:

            cursor.close()
            conn.close()

            flash(
                "Student not found.",
                "danger"
            )

            return redirect(
                url_for("students")
            )


        # =========================
        # GET COURSES
        # =========================

        cursor.execute("""
            SELECT
                id,
                course_name,
                course_code
            FROM courses
            WHERE status = 'Active'
            ORDER BY course_name ASC
        """)

        courses = cursor.fetchall()


        # =========================
        # POST
        # =========================

        if request.method == "POST":

            course_id = request.form.get(
                "course_id",
                ""
            ).strip()

            enrollment_date = request.form.get(
                "enrollment_date",
                ""
            ).strip()

            status = request.form.get(
                "status",
                "Active"
            ).strip()


            if not course_id:

                flash(
                    "Please select a course.",
                    "danger"
                )

                return render_template(
                    "assign_course.html",
                    student=student,
                    courses=courses
                )


            if status not in [
                "Active",
                "Completed",
                "Dropped"
            ]:

                status = "Active"


            # =========================
            # CHECK DUPLICATE
            # =========================

            cursor.execute("""
                SELECT id
                FROM student_courses
                WHERE student_id = %s
                  AND course_id = %s
            """, (
                id,
                course_id
            ))

            existing = cursor.fetchone()


            if existing:

                flash(
                    "This course is already assigned to this student.",
                    "danger"
                )

                return render_template(
                    "assign_course.html",
                    student=student,
                    courses=courses
                )


            # =========================
            # INSERT
            # =========================

            cursor.execute("""
                INSERT INTO student_courses (
                    student_id,
                    course_id,
                    enrollment_date,
                    status
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                id,
                course_id,
                enrollment_date or None,
                status
            ))


            conn.commit()

            cursor.close()
            conn.close()


            flash(
                "Course assigned successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "student_details",
                    id=id
                )
            )


        cursor.close()
        conn.close()


        return render_template(
            "assign_course.html",
            student=student,
            courses=courses
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )
# =========================
# UPDATE STUDENT COURSE STATUS
# =========================

@app.route(
    "/students/<int:student_id>/course/<int:course_id>/status",
    methods=["POST"]
)
def update_student_course_status(student_id, course_id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        status = request.form.get(
            "status",
            "Active"
        ).strip()

        if status not in [
            "Active",
            "Completed",
            "Dropped"
        ]:

            flash(
                "Invalid course status.",
                "danger"
            )

            cursor.close()
            conn.close()

            return redirect(
                url_for(
                    "student_details",
                    id=student_id
                )
            )


        cursor.execute("""
            SELECT id
            FROM student_courses
            WHERE id = %s
              AND student_id = %s
        """, (
            course_id,
            student_id
        ))

        enrollment = cursor.fetchone()


        if not enrollment:

            flash(
                "Course assignment not found.",
                "danger"
            )

        else:

            cursor.execute("""
                UPDATE student_courses
                SET status = %s
                WHERE id = %s
                  AND student_id = %s
            """, (
                status,
                course_id,
                student_id
            ))

            conn.commit()

            flash(
                "Course status updated successfully.",
                "success"
            )


        cursor.close()
        conn.close()

        return redirect(
            url_for(
                "student_details",
                id=student_id
            )
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )

    # =========================
# REMOVE STUDENT COURSE
# =========================

@app.route(
    "/students/<int:student_id>/course/<int:course_id>/remove",
    methods=["POST"]
)
def remove_student_course(student_id, course_id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        cursor.execute("""
            SELECT id
            FROM student_courses
            WHERE id = %s
              AND student_id = %s
        """, (
            course_id,
            student_id
        ))

        enrollment = cursor.fetchone()


        if not enrollment:

            flash(
                "Course assignment not found.",
                "danger"
            )

        else:

            cursor.execute("""
                DELETE FROM student_courses
                WHERE id = %s
                  AND student_id = %s
            """, (
                course_id,
                student_id
            ))

            conn.commit()

            flash(
                "Course removed successfully.",
                "success"
            )


        cursor.close()
        conn.close()

        return redirect(
            url_for(
                "student_details",
                id=student_id
            )
        )


    except mysql.connector.Error as error:

        return (
            f"Database Error: {error}",
            500
        )
# =========================
# APPLICATION START
# =========================

if __name__ == "__main__":
    app.run(debug=True)