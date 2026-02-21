import sqlite3
import os

DB_PATH = "data/jaia_meta.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables found:", [t[0] for t in tables])
        
        # Check audit_trail specifically
        if ('audit_trail',) in tables:
            print("audit_trail table exists.")
            cursor.execute("PRAGMA table_info(audit_trail);")
            columns = cursor.fetchall()
            print("Columns:", [c[1] for c in columns])
        else:
            print("audit_trail table MISSING!")

        conn.close()
    except Exception as e:
        print(f"Error checking DB: {e}")

if __name__ == "__main__":
    check_db()
