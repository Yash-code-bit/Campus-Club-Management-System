from flask import Flask, render_template, request, redirect, session
from db_connection import get_db

app = Flask(__name__)
app.secret_key = "supersecretkey"   # required for sessions



# ---------- Home Page ----------
@app.route("/")
def home():
    return render_template("home.html")



# ---------- Admin Login ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()

        cur.execute("""
            SELECT faculty_id, name 
            FROM faculty
            WHERE email=%s AND password=%s
        """, (email, password))

        row = cur.fetchone()
        db.close()

        if row:
            # VERY IMPORTANT FIX
            session.clear()   # remove any student_id that was stored earlier

            session["admin_id"] = row[0]
            session["admin_name"] = row[1]

            return redirect("/admin/dashboard")
        else:
            return render_template("admin_login.html", error="Invalid login")

    return render_template("admin_login.html")


# ------------ STUDENT LOGIN ------------
@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()

        cur.execute("""
            SELECT student_id, name
            FROM student
            WHERE email=%s AND password=%s
        """, (email, password))

        row = cur.fetchone()
        db.close()

        if row:
            session["student_id"] = row[0]
            session["student_name"] = row[1]
            return redirect("/student/dashboard")
        else:
            return render_template("student_login.html", error="Invalid login")

    return render_template("student_login.html")

# ------------ STUDENT DASHBOARD ------------
@app.route("/student/dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect("/student/login")

    return render_template("student_dashboard.html", name=session["student_name"])




# ---------- Admin Dashboard ----------
@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect("/admin/login")

    return render_template("admin_dashboard.html", name=session["admin_name"])

# ---------- ADMIN EVENT MANAGEMENT ----------
@app.route("/admin/events")
def admin_events():
    if "admin_id" not in session:
        return redirect("/admin/login")

    admin_id = session["admin_id"]

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT e.event_id, e.event_name, e.event_date, e.venue, e.status, c.club_name
        FROM event e
        JOIN club c ON e.club_id = c.club_id
        WHERE c.faculty_id = %s
        ORDER BY e.event_date ASC
    """, (admin_id,))

    events = cur.fetchall()
    db.close()

    return render_template("admin_events.html", events=events)



# ------------ EVENTS PAGE (Students + Admin) ------------
@app.route("/events")
def events():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT e.event_id, e.event_name, e.event_date, e.venue, e.status, c.club_name
        FROM event e
        JOIN club c ON e.club_id = c.club_id
        ORDER BY e.event_date ASC
    """)

    events = cur.fetchall()
    db.close()

    return render_template("events.html", events=events)

# ------------ REGISTER FOR EVENT ------------
@app.route("/register/<int:event_id>")
def register_event(event_id):

    if "student_id" not in session:
        return redirect("/student/login")

    student_id = session["student_id"]

    db = get_db()
    cur = db.cursor()

    # Check if already registered
    cur.execute("""
        SELECT * FROM event_registration
        WHERE event_id=%s AND student_id=%s
    """, (event_id, student_id))

    if cur.fetchone():
        db.close()
        return render_template("error.html",
                               message="You are already registered for this event.")

    # Register now
    cur.execute("""
        INSERT INTO event_registration (event_id, student_id, registration_date, status)
        VALUES (%s, %s, NOW(), 'registered')
    """, (event_id, student_id))

    db.commit()
    db.close()

    return render_template("error.html", message="Registration successful!")

# ---------- ADD EVENT ----------
@app.route("/admin/events/add", methods=["GET", "POST"])
def admin_add_event():
    if "admin_id" not in session:
        return redirect("/admin/login")

    admin_id = session["admin_id"]

    db = get_db()
    cur = db.cursor()

    # Fetch clubs assigned to this faculty
    cur.execute("SELECT club_id, club_name FROM club WHERE faculty_id=%s", (admin_id,))
    clubs = cur.fetchall()

    if request.method == "POST":
        club_id = request.form["club_id"]
        name = request.form["name"]
        date = request.form["date"]
        venue = request.form["venue"]
        status = request.form["status"]

        cur.execute("""
            INSERT INTO event (club_id, event_name, event_date, venue, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (club_id, name, date, venue, status))

        db.commit()
        db.close()

        return redirect("/admin/events")

    db.close()
    return render_template("admin_event_add.html", clubs=clubs)

# ---------- EDIT EVENT ----------
@app.route("/admin/events/edit/<int:event_id>", methods=["GET", "POST"])
def admin_edit_event(event_id):
    if "admin_id" not in session:
        return redirect("/admin/login")

    admin_id = session["admin_id"]

    db = get_db()
    cur = db.cursor()

    # fetch event
    cur.execute("""
        SELECT event_id, club_id, event_name, event_date, venue, status
        FROM event
        WHERE event_id=%s
    """, (event_id,))
    event = cur.fetchone()

    # faculty’s clubs
    cur.execute("SELECT club_id, club_name FROM club WHERE faculty_id=%s", (admin_id,))
    clubs = cur.fetchall()

    if request.method == "POST":
        club_id = request.form["club_id"]
        name = request.form["name"]
        date = request.form["date"]
        venue = request.form["venue"]
        status = request.form["status"]

        cur.execute("""
            UPDATE event
            SET club_id=%s, event_name=%s, event_date=%s, venue=%s, status=%s
            WHERE event_id=%s
        """, (club_id, name, date, venue, status, event_id))

        db.commit()
        db.close()

        return redirect("/admin/events")

    db.close()
    return render_template("admin_event_edit.html", event=event, clubs=clubs)

# ---------- DELETE EVENT ----------
@app.route("/admin/events/delete/<int:event_id>")
def admin_delete_event(event_id):
    if "admin_id" not in session:
        return redirect("/admin/login")

    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM event WHERE event_id=%s", (event_id,))
    db.commit()
    db.close()

    return redirect("/admin/events")

# ------------ MY REGISTRATIONS PAGE ------------
@app.route("/my_registrations")
def my_registrations():
    if "student_id" not in session:
        return redirect("/student/login")

    student_id = session["student_id"]

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT e.event_name, e.event_date, e.venue, er.status
        FROM event_registration er
        JOIN event e ON er.event_id = e.event_id
        WHERE er.student_id=%s
        ORDER BY e.event_date DESC
    """, (student_id,))

    registrations = cur.fetchall()
    db.close()

    return render_template("my_registrations.html", registrations=registrations)

# ------------ MY CERTIFICATES ------------
@app.route("/my_certificates")
def my_certificates():
    if "student_id" not in session:
        return redirect("/student/login")

    student_id = session["student_id"]

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT c.certificate_id, e.event_name, c.issue_date, c.certificate_link
        FROM certificate c
        JOIN event e ON c.event_id = e.event_id
        WHERE c.student_id=%s
        ORDER BY c.issue_date DESC
    """, (student_id,))

    certificates = cur.fetchall()
    db.close()

    return render_template("my_certificates.html", certificates=certificates)

# ---------- ADMIN: View registrations & issue certificate ----------
@app.route("/admin/certificates")
def admin_certificates():
    if "admin_id" not in session:
        return redirect("/admin/login")

    admin_id = session["admin_id"]

    db = get_db()
    cur = db.cursor()

    # Fetch events of this faculty
    cur.execute("""
        SELECT event_id, event_name
        FROM event
        WHERE club_id IN (
            SELECT club_id FROM club WHERE faculty_id=%s
        )
    """, (admin_id,))
    events = cur.fetchall()

    db.close()
    return render_template("admin_certificates.html", events=events)

# ---------- ADMIN: View registrations for one event ----------
@app.route("/admin/certificates/event/<int:event_id>")
def admin_event_registrations(event_id):
    if "admin_id" not in session:
        return redirect("/admin/login")

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT e.event_name
        FROM event e
        WHERE e.event_id=%s
    """, (event_id,))
    event = cur.fetchone()

    # Registered students
    cur.execute("""
        SELECT s.student_id, s.name, s.email
        FROM event_registration er
        JOIN student s ON er.student_id = s.student_id
        WHERE er.event_id=%s
    """, (event_id,))
    students = cur.fetchall()

    db.close()

    return render_template("admin_event_students.html",
                           event=event,
                           students=students,
                           event_id=event_id)

# ---------- ISSUE CERTIFICATE ----------
@app.route("/admin/certificates/issue/<int:event_id>/<int:student_id>")
def issue_certificate(event_id, student_id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    db = get_db()
    cur = db.cursor()

    #  certificate link (demo purpose)
    fake_link = "/static/certificates/demo_certificate.pdf"

    cur.execute("""
        INSERT INTO certificate (event_id, student_id, issue_date, certificate_link)
        VALUES (%s, %s, NOW(), %s)
    """, (event_id, student_id, fake_link))

    db.commit()
    db.close()

    return render_template("error.html",
                message="Certificate issued successfully! (Demo Link Created)")


  





# Run App
if __name__ == "__main__":
    app.run(debug=True)


