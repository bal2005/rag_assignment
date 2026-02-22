import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

load_dotenv()

DB_USER = os.getenv("DB_USER_NEON")
DB_PASSWORD = os.getenv("DB_PW_NEON")
DB_HOST = os.getenv("DB_NEON_HOST")
DB_NAME =os.getenv("DB_NEON_NAME")


DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?sslmode=require&channel_binding=require"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM contracts"))
    rows = result.fetchall()

    for row in rows:
        print(row)