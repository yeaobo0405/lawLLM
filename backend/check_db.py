import sqlite3
import os

db_path = "d:/develop1/law03/backend/data/conversation_memory.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(conversations)")
        columns = cursor.fetchall()
        print("Columns in 'conversations':")
        for col in columns:
            print(col)
            
        cursor.execute("PRAGMA table_info(summaries)")
        columns = cursor.fetchall()
        print("\nColumns in 'summaries':")
        for col in columns:
            print(col)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print(f"Database not found at {db_path}")
