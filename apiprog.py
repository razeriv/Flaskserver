from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret-key"

jwt = JWTManager(app)


def get_db():
    return psycopg2.connect(
        host="localhost",
        database="mydb",
        user="iam_user",
        password="12345678",
        cursor_factory=RealDictCursor
    )


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    
    first_name = data.get("name")
    last_name = data.get("surname")
    email = data.get("email")
    faculty = data.get("faculty")
    group_number = data.get("group")
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
            INSERT INTO users 
            (first_name, last_name, email, faculty, group_number, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (first_name, last_name, email, faculty, group_number, hashed_password))

        user_id = cur.fetchone()["id"]
        conn.commit()

        token = create_access_token(identity=str(user_id))

        return jsonify({
            "message": "Registration successful",
            "token": token,
            "user": {
                "id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "faculty": faculty,
                "group_number": group_number
            }
        }), 201

    except Exception as e:
        conn.rollback()
        print("=== REGISTRATION ERROR ===")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    login = data.get("username") or data.get("email")
    password = data.get("password")

    if not login or not password:
        return jsonify({"error": "Login (email or username) and password required"}), 400

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, password_hash 
            FROM users 
            WHERE email = %s
        """, (login,))
        
        user = cur.fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid credentials"}), 401

        token = create_access_token(identity=str(user["id"]))
        return jsonify({"token": token, "message": "Login successful"}), 200

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500
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
            SELECT 
                id, 
                email, 
                first_name, 
                last_name, 
                faculty, 
                group_number,
                role,
                is_active,
                is_verified,
                about,
                created_at
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify(user), 200
    finally:
        cur.close()
        conn.close()


@app.route("/projects", methods=["GET"])
def get_projects():
    conn = get_db()
    cur = conn.cursor()
    try:
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
