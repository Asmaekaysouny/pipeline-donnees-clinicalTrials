import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(".env")

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

sql = Path("sql/queries.sql").read_text(encoding="utf-8-sig")

with conn.cursor() as cur:
    for i, query in enumerate(sql.split(";"), 1):
        if query.strip():
            print(f"\n========== REQUÊTE {i} ==========")
            cur.execute(query)
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                print(" | ".join(columns))
                for row in cur.fetchall():
                    print(" | ".join(str(value) for value in row))

conn.close()
