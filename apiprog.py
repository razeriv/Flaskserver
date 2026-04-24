from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret-key-change-in-production-2026"
jwt = JWTManager(app)


def get_db():
    return psycopg2.connect(
        host="localhost",
        database="Tech",
        user="admin2",
        password="admin",
        cursor_factory=RealDictCursor
    )

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    name = data.get("name")
    surname = data.get("surname")
    email = data.get("email")
    faculty = data.get("faculty")
    group = data.get("group")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return jsonify({"error": "User with this email already exists"}), 409

        hashed_password = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users (name, surname, email, faculty, "group", password)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (name, surname, email, faculty, group, hashed_password))

        user_id = cur.fetchone()["id"]
        conn.commit()

        token = create_access_token(identity=user_id)

        return jsonify({
            "message": "Registration successful",
            "token": token,
            "user": {
                "id": user_id,
                "email": email,
                "name": name,
                "surname": surname
            }
        }), 201

    except psycopg2.Error as e:
        conn.rollback()
        print("Database error:", e)
        return jsonify({"error": "Database error", "details": str(e)}), 500
    except Exception as e:
        conn.rollback()
        print("Unexpected error:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT id, password FROM users WHERE username = %s OR email = %s",
            (username, username)
        )
        user = cur.fetchone()

        if not user or not check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid credentials"}), 401

        token = create_access_token(identity=user["id"])

        return jsonify({"token": token})

    finally:
        cur.close()
        conn.close()

@app.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, username, name, surname, email, faculty, "group"
            FROM users WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()
        return jsonify(user) if user else jsonify({"error": "User not found"}), 404
    finally:
        cur.close()
        conn.close()

@app.route("/projects", methods=["GET"])
def get_projects():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, id_tutor, title, description, requirements, details,
                   tutor as instructor, topic, difficulty, deadline
            FROM projects
        """)
        projects = cur.fetchall()
        return jsonify(projects)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/")
def home():
    return "CourseIT API is running 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
