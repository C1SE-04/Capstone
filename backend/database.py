# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Cú pháp: postgresql://<username>:<password>@<host>:<port>/<db_name>
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_LgvPyk9znt8p@ep-withered-forest-b37ql1e0-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

# SQLAlchemy 2.x mặc định dùng psycopg3 khi URL là "postgresql://".
# Ép sang psycopg2 để tương thích với psycopg2-binary trong requirements.txt.
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# PostgreSQL không cần connect_args={"check_same_thread": False} như SQLite
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()