from flask import Flask, render_template, request, jsonify
from email_validation import validate_email, EmailNotValidError
from configuration.db import get_connection
from auth.authentication import auth_bp
from config import config
from extension import bcrypt, jwt, cors, oauth
app = Flask(__name__)
bcrypt.init_app(app)
app.register_blueprint(auth_bp, url_prefix="/api/auth")
jwt.init_app(app)
oauth.init_app(app)
cors.init_app(app, resources={r"http://localhost:3000/*": {"origins": "*"}})
app.config.from_object(config)
@app.route("/")
def check_connection():
    conn = None

    try:
        conn = get_connection()

        if conn:
            return "<h1>MySQL Connection successful!</h1>"
        
        return "<h1>MySQL Connection failed!</h1>"

    except Exception as e:
        return f"<h1>connection error: {e}</h1>"

    finally:
        if conn:
            conn.close()

@app.route("/users")
def home():
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                                SELECT * FROM users
                            """)
            all_users = cursor.fetchall()
        return render_template("app.html", users=all_users)
    except Exception as e:
        print(f"Error. occur: {e}")
    finally:
        if conn:
            conn.close()

@app.route("/adduser", methods=["POST"])
def add_user():
    data = request.json
    lname = data["lastname"]
    fname = data.get("firstname")
    mail = data.get("mail")
    password = data.get("password")
    role = data.get("role")

    if not lname.strip():
        if not lname or len(lname) < 3:
            return jsonify({"success": False, "message":  "Lastname cannot be empty or abbreviated."}), 400
    
    if not fname.strip():
        if not fname or len(lname) < 3:
            return jsonify({"success": False, "message":  "Firstname cannot be empty or abbreviated."}), 400


    if not mail:
        return jsonify({"success": False, "message":  "Mail cannot be empty."})
    try:
        valid_email = validate_email(mail)
        mail = valid_email.normalized
    except EmailNotValidError as e:
        return jsonify({"message": str(e)}), 400
    
    if not password:
        return jsonify({"success": False, "message":  "Password cannot be empty."})
    
    password = bcrypt.generate_password_hash(password)
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users(lastname, firstname, email, password, role) VALUES
                (%s, %s, %s, %s, %s)
                """, (lname, fname, mail, password, role)
            )
            conn.commit()
            return jsonify({"success": True, "message":  "User added successfully"}), 201
    except Exception as e:
        return jsonify({"success": False, "message":  f"Error {e}"}), 500
    finally:
        if conn:
            conn.rollback()
        conn.close()
    # print(lastname + firstname)
if __name__ == "__main__":
    app.run(port=3000, debug=True)