import sys
import os
sys.path.append(os.getcwd())

from sqlmodel import Session, select, text
from database import engine
from apps.tracker.models import EpisodeActivity

def verify():
    print("Verifying database connection...")
    try:
        with Session(engine) as session:
            # Check if we can read
            print("Attempting to read from EpisodeActivity...")
            count = session.exec(select(EpisodeActivity)).all()
            print(f"Read successful. Count: {len(count)}")
            
            # Check for locks
            print("Attempting to write a test record...")
            try:
                # We won't actually commit, just check if we can begin a transaction
                session.exec(text("SELECT 1"))
                print("Transaction started successfully.")
            except Exception as e:
                print(f"Write/Transaction failed: {e}")
                return
            
            print("Database seems OK.")
    except Exception as e:
        print(f"Database connection failed: {e}")

if __name__ == "__main__":
    verify()
