from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity)
import psycopg2

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = "super-secret-key"
jwt = JWTManager(app)

def get_db():
    return psycopg2.connect(
        host="localhost",
        database="Tech",
        user="admin2",
        password="admin"
    )

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM users WHERE username=%s AND password=%s",
        (username, password)
    )
    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=user[0])
    return jsonify({"token": token})

@app.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    user_id = get_jwt_identity()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT username FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    return jsonify({
        "id": user_id,
        "username": user[0]
    })

@app.route("/projects", methods=["GET"])
def get_projects():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, id_tutor, title, description, requirements, details,
                   tutor, topic, difficulty, deadline, status
            FROM projects
        """)

        rows = cur.fetchall()

        cur.close()
        conn.close()

        projects = []
        for row in rows:
            projects.append({
                "id": row[0],
                "id_tutor": row[1],
                "title": row[2],
                "description": row[3],
                "requirements": row[4],
                "details": row[5],
                "instructor": row[6],
                "topic": row[7],
                "difficulty": row[8],
                "deadline": str(row[9]) if row[7] else None
            })

        return jsonify(projects)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "API is running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)