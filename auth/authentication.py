

from flask import Blueprint, request, jsonify, url_for 
from email_validator import validate_email, EmailNotValidError
import oauth
from email_service import send_verification_email
from extension import bcrypt, jwt
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
            verification_link = f"https://event-management-system-anx3.onrender.com/verify-email/{verification_token}"
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

            access_token = jwt.create_access_token(identity=user["id"],
                                                    additional_claims={"role": user["role"]})
            return jsonify({"success": True,
                            "message": "Login successful.",
                            "access_token": access_token,
                            "user": {
                                "id": user["id"],
                                "name": user["name"],
                                "email": user["email"],
                                "role": user["role"]
                            }}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})


    @auth_bp.route("/forget-password", methods=["POST"])
    def forget_password():
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Data cannot be empty."})

        email = data.get("email")
        if not email:
            return jsonify({"success": False, "message": "Email cannot be empty."}), 400

        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                                SELECT id, name FROM users WHERE email = %s
                            """, (email,))
                user = cursor.fetchone()
                if not user:
                    return jsonify({"success": False, "message": "User not found!"}), 404

                reset_token = secrets.token_urlsafe(32)
                cursor.execute("""
                                UPDATE users SET reset_token = %s WHERE id = %s
                            """, (reset_token, user["id"]))
                conn.commit()

                reset_link = f"https://event-management-system-anx3.onrender.com/reset-password/{reset_token}"
                html=f"""
                    <html›
                        <body>
                            <h1>Password Reset Request</h1>
                            <p>Click below to reset your password.</p>
                            <a href="(reset_link)">Reset Password</a>
                        </body>
                    </htmL>
                """
            send_verification_email(email, "Reset Password", html)
            
            return jsonify({"success": True, "message": "Password reset link sent to your email."}), 200
        except Exception as e:
            return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
        finally: 
            if conn:
                    conn.close()


@auth_bp.route("/reset-password/<token>", methods=["POST"])
def reset_password (token):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Data cannot be empty."}), 400

    new_password = data.get ("new_password")
    if not new_password:
        return jsonify({"success": False, "message": "New password cannot be empty."}), 400
    
    if len(new_password)<6:
        return jsonify({"success": False, "message": "New password must be at least 6 characters long."}), 400
    
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                            SELECT id FROM users WHERE reset_token = %s AND expires_at > NOW()
                        """, (token,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "Invalid or expired reset token."}), 400
            
            hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")
            cursor.execute("""
                            UPDATE users SET password = %s, reset_token = NULL, expires_at = NULL WHERE id = %s
                        """, (hashed_password, user["id"]))
            return jsonify({"success": True, "message": "Password reset successful."}), 200
    except Exception as e:
        return jsonify({""}), 500
    finally:
        cursor.close()
        conn.close()

@auth_bp.route("/google", methods=["GET"])
def google_login():
    redirect_uri = url_for("http://event-management-system-anx3.onrender.com/api/auth/google/callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route("/google/callback", methods=["GET"])
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = token.get("userinfo")
    if not user_info:
        #return jsonify({"success": False, "message": "Failed to retrieve user information from Google."}), 400
    
        email = user_info.get("email")
        name = user_info.get("name")
        google_id = user_info.get("sub")
    if not email or not name:
        return jsonify({"success": False, "message": "Email or name not found in Google user information."}), 400
    
        #check if user already exists in the database
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                            SELECT u.id, u.name, u.email, u.role FROM OAuthAccount o 
                            JOIN users u ON o.user_id = u.id
                            WHERE o.provider = 'google' AND o.google_id = %s
                        """, (google_id,))
            user = cursor.fetchone()
            if user:
                user_id = user["id"]
            else:
                #check if user with the same email already exists
                cursor.execute("""
                                SELECT id FROM users WHERE email = %s
                            """, (email,))
                existing_user = cursor.fetchone()
                if existing_user:
                    user_id = existing_user["id"]
                else:
                    # Create new user in the database
                    cursor.execute("""
                                    INSERT INTO users (name, email, is_verified) VALUES (%s, %s, TRUE)
                                """, (name, email))
                    user_id = cursor.lastrowid
    except Exception as e:
            return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
    except Exception as e:
            return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
