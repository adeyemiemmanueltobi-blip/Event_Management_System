from flask import Blueprint, request, jsonify
from email_validator import validate_email, EmailNotValidError
from email_service import send_verification_email
from extension import bcrypt
import secrets
auth_bp = Blueprint ("auth", __name__)
from configuration.db import get_connection

@auth_bp.route("/adduser", methods= ["POST"])
def register():
    data = request.get_json
    if not data:
        return jsonify({"success": False, "message": "Data must not be empty."})
    name = data.get("name")
    email = data.get("mail")
    password = data.get ("password")
    role = data.get ("role")

    if not name:
        return jsonify({"success": False, "message": "name cannot be empty."}), 400

    if role not in ["VENDOR", "WAITER"]:
        return jsonify({"success": False, "message": "Choose a valid role."}), 400

    if not email:
        return jsonify ({"success": False, "message": "Mail cannot be empty."})

    if not password:
        return jsonify({"success": False, "message": "password cannot be empty"})

    name = name.strip()
    email = email.strip().lower()

    if len(name) < 2:
        return jsonify({"success": False, "message": "Name must contain at least 3 character."})

    if len(name) > 100:
        return jsonify({
            "success": False, "message": "Name cannot exceed 100 character."
        })

    if len(email) > 255:
        return jsonify({
            "success": False,
            "message": "Email cannot exceed 255 character."
        })

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must contain at least 8 characters."
        })
    try:
        validate_email(email)
    except EmailNotValidError as e:
        print(f"Error: {str(e)}")

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    verification_token = secrets.token_urlsafe(32)
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (name, email, password, role, verification_token)
                VALUES (%s, %s, %s, %s, %s)
                """, (name, email, hashed_password, role, verification_token))

            conn.commit()
            verification_link = f"http://127.0.0.1:5000/={verification_token}"
            html="""
                    <html>
                        <body>
                            <h1>Welcome {name}!</h1>
                            <p>Click below to verify your account.</p>
                            <a href="{verification_link}">Verify Account</a>
                        </body>
                    </html>                    
                """
            send_verification_email(email, "Verify Email", html)

            return jsonify({
                "success": True,
                "message": "User registered successfully."
            }), 201
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to register user", "error": str(e)}), 500
    finally:
        conn.close()


@auth_bp.route("/verify-email/<token>", methods=["GET"])
def verify_email(token):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                            SELECT id FROM users 
                            WHERE verification_token = %
                            """, (token,))

            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "User not found!"})

            cursor.execute("""
                            UPDATE users SET is_verified = TRUE,
                            verification_token = NULL WHERE id = %s
                        """, (user["id"],))
            return jsonify({"success": True, "message": "User Verified successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: ({str(e)})"})

@auth_bp. route("/login", methods=["POST"])
def login(request):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Data cannot be empty."})

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and Password cannot be empty."}), 400
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                                SELECT id, name, email, password, role, is_verified FROM users WHERE email = %s 
                            """ (email))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "invalid email or password!"}), 400

            if not bcrypt.check_password_hash(user["password"], password):
                return jsonify({"success": False, "message": "Incorrect password!"}), 401

            if not user["is_verified"]:
                return jsonify({"success": False, "message": "Please verify your email before loggin in."}), 403

            return jsonify({"success": True,
                            "message": "Login successful.",
                            "user": {
                                "id": user["id"],
                                "name": user["name"],
                                "email": user["email"],
                                "role": user["role"]
                            }}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})