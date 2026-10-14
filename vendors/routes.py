from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from configuration.db import get_connection

vendor_bp = Blueprint("vendors", __name__)

@vendor_bp.routes("/profile", methods=["POST"])
@jwt_required
def create_vendor_profile():
    data = request.get_json()

    business_name = data.get("business_name")
    description = data.get("description")
    phone = data.get("phone")
    location = data.get("location")

    if not business_name:
        return jsonify({"success": False, "message": "Business name is required"}), 400
    
    user_id = int(get_jwt_identity())
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                            SELECT id, role FROM users WHERE id=%s
                            """, (user_id))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 404
            
            if user["role"] != "VENDOR":
                return jsonify({"success": False, "message": "Only vendors can upload profile"})
            
            cursor.execute("""
                            SELECT id FROM vendor_profile WHERE user_id=%s
                            """, (user_id))
            user = cursor.fetchone()
            if user:
                return jsonify({"message": "Vendor profile already exist"}), 409
            
            
            cursor.execute("""
                            INSERT INTO vendor_profile (
                            user_id, 
                            business_name,  
                            description, 
                            phone, 
                            location)
                            VALUES (%s, %s, %s, %s, %s)
                            """, (user_id, business_name, description, phone, location))
            vendor_id = cursor.lastrowid

        conn.commit()
        return jsonify({
            "success": True, 
            "message": "Vendor profile create successfully!", 
            "vendor_id": vendor_id, 
            "verification_status": "PENDING"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Error {str(e)}"}), 500