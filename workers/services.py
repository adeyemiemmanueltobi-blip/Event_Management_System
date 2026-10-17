from flask import jsonify

from configuration.db import get_connection

def create_worker_profile(bio, user_id, location, experience_years, expected_date):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                                SELECT id, role FROM users WHERE user_id = %s
                                """, (user_id,))

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
                return jsonify({"success": False, "message": "worker profile exist"}), 400

            cursor.execute("""
                            INSERT INTO workers_profile(user_id, bio, experience_years, locationx, expected_rate) VALUES(%s, %s, %s, %s, %s)
                            """, (user_id, bio, experience_years, location, expected_date))

            worker_id = cursor.lastrowid

            conn.commit()

            return{}
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    