from flask import jsonify

from configuration.db import get_connection

def create_workers_profile(bio, user_id, location, experience_years, expected_date):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                                SELECT id, role FROM users Where id = %s
                                """, (user_id))
            
            user = cursor.fetchone()

            if not user:
                return jsonify({"success": False, "message": "User is not found"}), 404
            
            if user["role"] != "WORKER":
                return jsonify({"success": False, "message": "Only workers can make a profile update"}), 400
            
            cursor.execute("""
                                SELECT id FROM worker_profile WHERE user_id = %s
                                """, (user_id))
            user = cursor.fetchone()
            if user:
                return jsonify({"success": False, "message": "Worker profile already exist"}), 409
            
            cursor.execute("""
                                INSERT INTO workers_profile(user_id, bio, experience_years, location, expected_rate) 
                                VALUES (%s, %s, %s, %s, %s) 
                            """, (user_id, bio, experience_years, location, expected_date))
            
            worker_id = cursor.lastrowid
            
            conn.commit()

            return {
                "sucess": True, 
                "message": "Worker profile created successfully",
                "worker_id":  worker_id,
                "status": 201
            }

    except Exception:
        conn.rollback()
    finally:
        conn.close()
