import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
import models

def sync_tables():
    print("Checking and creating tables on NeonDB...")
    models.Base.metadata.create_all(bind=engine)
    print("Successfully synchronized tables (including session_active_intervals)!")

if __name__ == "__main__":
    sync_tables()
