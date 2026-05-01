from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
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

    first_name = data.get("first_name") or data.get("name")
    last_name = data.get("last_name") or data.get("surname")
    email = data.get("email")
    course = data.get("course") or data.get("faculty")
    group_number = data.get("group_number") or data.get("group")
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
            INSERT INTO users (first_name, last_name, email, course, group_number, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (first_name, last_name, email, course, group_number, hashed_password))

        user_id = cur.fetchone()["id"]
        conn.commit()

        token = create_access_token(identity=str(user_id))

        return jsonify({
            "message": "Registration successful",
            "token": token,
            "user": {
                "id": str(user_id),
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "course": course,
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
    login = data.get("email") or data.get("username")
    password = data.get("password")

    if not login or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (login,))
        user = cur.fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid credentials"}), 401

        token = create_access_token(identity=str(user["id"]))
        return jsonify({"message": "Login successful", "token": token}), 200

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
            SELECT id, email, first_name, last_name, course, group_number,
                   role, is_active, is_verified, about, created_at, updated_at
            FROM users WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user), 200
    finally:
        cur.close()
        conn.close()

@app.route("/profile", methods=["PATCH"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    about = data.get("about")

    if about is None:
        return jsonify({"error": "Поле 'about' обязательно"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE users 
            SET about = %s, 
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, email, first_name, last_name, course, group_number,
                      role, is_active, is_verified, about, created_at, updated_at
        """, (about, user_id))

        updated_user = cur.fetchone()

        if not updated_user:
            return jsonify({"error": "Пользователь не найден"}), 404

        conn.commit()
        return jsonify(updated_user), 200

    except Exception as e:
        conn.rollback()
        print("=== UPDATE PROFILE ERROR ===")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500

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

@app.route("/projects", methods=["POST"])
@jwt_required()
def create_project():
    data = request.get_json() or {}
    user_id = get_jwt_identity()

    title = data.get("title")
    description = data.get("description")
    topic = data.get("topic") or "Другое"
    status = data.get("status") or "открыт"
    difficulty = data.get("difficulty")
    deadline = data.get("deadline")

    if not title or not description:
        return jsonify({"error": "Title and description are required"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO projects 
                (id_tutor, title, description, topic, status, difficulty, deadline, tutor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 
                    (SELECT first_name || ' ' || last_name FROM users WHERE id = %s))
            RETURNING id, title, description, topic, status, difficulty, deadline
        """, (user_id, title, description, topic, status, difficulty, deadline, user_id))

        new_project = cur.fetchone()
        conn.commit()

        return jsonify({
            "message": "Project created successfully",
            "project": new_project
        }), 201

    except Exception as e:
        conn.rollback()
        print("=== CREATE PROJECT ERROR ===")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/")
def home():
    return "CourseIT API is running 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
