import os
db_path = "d:/develop1/law03/backend/data/conversation_memory.db"
if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print(f"Successfully deleted {db_path}")
    except Exception as e:
        print(f"Error deleting file: {e}")
else:
    print(f"File {db_path} does not exist.")
