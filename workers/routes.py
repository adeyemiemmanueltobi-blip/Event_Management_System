from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from configuration.db import get_connection
worker_bp = Blueprint("workers", __name__)

@worker_bp.route("/profile", methods=["POST"])
@jwt_required()
def create_worker_profile():
    data = request.get_json()

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    phone = data.get("phone")
    location = data.get("location")

    if not first_name:
        return jsonify({"success": False, "message": "First name is required"}), 400
    
    user_id = int(get_jwt_identity())
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                            SELECT id, role FROM users WHERE id=%s
                            """, (user_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 404
            
            if user["role"] != "WORKER":
                return jsonify({"success": False, "message": "Only workers can upload profile"})
            
            cursor.execute("""
                            SELECT id FROM worker_profile WHERE user_id=%s
                            """, (user_id,))
            existing_profile = cursor.fetchone()
            if existing_profile:
                return jsonify({"message": "Worker profile already exists"}), 409
            
            cursor.execute("""
                            INSERT INTO worker_profile (
                            user_id, 
                            first_name,  
                            last_name, 
                            phone, 
                            location)
                            VALUES (%s, %s, %s, %s, %s)
                            """, (user_id, first_name, last_name, phone, location))
            worker_id = cursor.lastrowid

        conn.commit()
        return jsonify({
            "success": True, 
            "message": "Worker profile created successfully!", 
            "worker_id": worker_id}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Error {e}"}), 500
    finally:
        if conn:
            conn.close()