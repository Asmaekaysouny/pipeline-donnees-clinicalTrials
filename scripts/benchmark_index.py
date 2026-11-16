import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env")

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

query = """
SELECT COUNT(*)
FROM studies
WHERE status = 'RECRUITING';
"""

try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT to_regclass('public.idx_studies_status')
        """)
        index_exists = cur.fetchone()[0] is not None

        if index_exists:
            print("L'index existe déjà : comparaison avant/après impossible.")
        else:
            print("\n===== AVANT CREATION DE L'INDEX =====")
            cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + query)
            for row in cur.fetchall():
                print(row[0])

            print("\n===== CREATION DE L'INDEX =====")
            cur.execute("""
                CREATE INDEX idx_studies_status
                ON studies(status)
            """)
            cur.execute("ANALYZE studies")
            conn.commit()
            print("Index créé avec succès.")

            print("\n===== APRES CREATION DE L'INDEX =====")
            cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + query)
            for row in cur.fetchall():
                print(row[0])

finally:
    conn.close()
