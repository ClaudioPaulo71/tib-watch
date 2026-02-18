import sqlite3

def add_columns():
    conn = sqlite3.connect('data/tib_watch.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE media ADD COLUMN number_of_seasons INTEGER")
        print("Added number_of_seasons column")
    except sqlite3.OperationalError as e:
        print(f"number_of_seasons column might already exist: {e}")

    try:
        cursor.execute("ALTER TABLE media ADD COLUMN cast TEXT")
        print("Added cast column")
    except sqlite3.OperationalError as e:
        print(f"cast column might already exist: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_columns()
