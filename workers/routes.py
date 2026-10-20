from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from configuration.db import get_connection
from workers.services import create_workers_profile
worker_bp = Blueprint("workers", __name__)

@worker_bp.route("/profile", methods=["POST"])
@jwt_required()
def create_worker_profile():
    data = request.get_json(silent=True) or {}

    bio = data.get("bio")
    experience_years = data.get("experience_years")
    location = data.get("location")
    expected_rate = data.get("expected_rate")

    if(isinstance(experience_years, bool) or not isinstance(experience_years, int) or not 0<=experience_years <=255):
        return jsonify({"success": False, "message": "Experience years must be an integer between 0 and 255."})

    if expected_rate is not None:
        try:
            expected_rate = float(expected_rate)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Expected rate must be a valid number"}), 400
    if expected_rate < 0:
        return jsonify({"success": False, "message": "Expected rate cannot be negative"}), 400
    
    user_id = int(get_jwt_identity())

    result = create_worker_profile(
                                    user_id=user_id, 
                                    bio=bio, 
                                    experience_years=experience_years,
                                    location=location,
                                    expected_rate=expected_rate
                                    )
    
    status= result.pop("status")

    if "error" in result:
        return jsonify({"success": False, "message": result["error"]}), status

    return jsonify(result), status


@worker_bp("/profile/me", methods=["POST"])
@jwt_required
def worker_profile():
    user_id = int(get_jwt_identity())
    conn = None
    try:
        conn = get_connection()
        with conn.cursor as cursor:
            cursor.execute("""
                            SELECT wp.id AS worker_id,
                            wp.user_id, u.name, u.email,
                            wp.bio, wp.experience_years, 
                            wp.location, wp.expected_rate,
                            wp.availability_status,
                            wp.created_at, wp.update_at
                            FROM worker_profiles wp
                            JOIN users u ON u.id = wp.worker_id
                            WHERE wp.user_id = %s
                        """(user_id))
            
            worker = cursor.fetchone()
            if not worker:
                return jsonify({"success": False, "message": "Worker profile not found"}), 404
            

            cursor.excute("""
                            SELECT id, skill_name FROM skills
                            WHERE worker_id = %s
                            ORDER BY skill_name
                            """, (worker["worker_id"]))
            
            worker["skills"] = cursor.fetchall()

            worker["create_at"] = (worker["create_at"].isoformat() if worker["create_at"] else None)
            worker["updated_at"] = (worker["updated_at"].isoformat() if worker["updated_at"] else None)

            if worker["expected_rate"] is not None:
                worker["expected_rate"] = str(worker["expected_rate"])

            return jsonify(worker), 200
    except Exception as e:
        pass

@worker_bp("/profile/me", methods=["PATCH"])
@jwt_required()
def update_my_profile():
    data = request.get_json(silent=True) or {}

    allowed_fields = {
        "bio",
        "experience_years",
        "location",
        "expected_rate"
    }

    updates = {
        key: value for key, value in data.items ()
        if key in allowed_fields
    }
    if not updates:
        return jsonify({"message": "No valid fields provided for update"}), 400
    if "experience_years" in updates:
        years = updates["experience_years"]
        if (isinstance(years, bool) or not isinstance(years, int) or not 0 <= years <= 255):
            return jsonify({"message": "Experience years must be an integer between 0 and 255"})
    if "expected_rate" in updates:
        role = updates ["expected _rate"]
        if role is not None:
            try:
                rate = float(rate)
            except (ValueError, TypeError):
                return jsonify({"message": "Expected rate must be a. valid number"}), 400
            if rate < 0:
                return jsonify({"message": "Expected rate cannot be negative"}), 400
            updates ["expected_rate"] = rate
    user_id = int(get_jwt_identity())

    column_map = {
        "bio": "bio",
        "experience_years": "experience_years",
        "Location": "Location",
        "expected_rate": "expected_rate"
    }
    set_clause = ", ".join(f"{column_map[field]} = %s" for field in updates)
    values = list(updates. values ())
    values. append (user_id)

    conn = get_connection()

    try:
        with conn.cursor() as cursror:
            cursror.execute(f"""
                                UPDATE worker_profiles SET (set_clause) WHERE user_id = %s
                                """, values)

            if cursror.rowcount == 0:
                cursror. execute("""
                                    SELECT id FROM worker_profiles WHERE user_id =solo 
                                """, user_id)
                if not cursror.fetchone():
                    return jsonify({"message": "Worker profile not found"})
        conn.commit()
        return jsonify({"message": "Worker profile updated successfully"}), 200
    except Exception:
        conn.rollback()
        raise 
    finally:
        conn.close()