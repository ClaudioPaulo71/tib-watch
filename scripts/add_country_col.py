from sqlmodel import create_engine, text
import os

# Adjust path to where your DB is located relative to this script or use absolute path
DATABASE_URL = "sqlite:///data/tib_watch.db" 

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        try:
            # Check if column exists (simple way for sqlite)
            result = connection.execute(text("PRAGMA table_info(user)"))
            columns = [row.name for row in result]
            
            if "country" not in columns:
                print("Adding 'country' column to 'user' table...")
                connection.execute(text("ALTER TABLE user ADD COLUMN country VARCHAR"))
                print("Migration successful!")
            else:
                print("'country' column already exists.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
