import psycopg2

DB_NAME = "Tech"
DB_USER = "admin2"
DB_PASSWORD = "admin"
DB_HOST = "localhost"

def create_database():
    conn = psycopg2.connect(
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST
    )
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(f"CREATE DATABASE {DB_NAME};")

    cur.close()
    conn.close()

def run_schema():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST
    )
    cur = conn.cursor()

    with open("Tech.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    cur.execute(sql)

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    create_database()
    run_schema()
    print("Database created successfully!")