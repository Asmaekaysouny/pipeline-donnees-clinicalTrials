"""Exécute chaque requête d'un fichier SQL et affiche les premières lignes et la durée."""
import os
import sys
import time

import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"), dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
)
conn.autocommit = True
cur = conn.cursor()

text = open(sys.argv[1], encoding="utf-8-sig").read()
for stmt in (s.strip() for s in text.split(";")):
    lines = stmt.splitlines()
    if not any(l.strip() and not l.strip().startswith("--") for l in lines):
        continue
    title = next((l for l in lines if l.strip().startswith("--")), "-- (sans titre)")
    print("\n" + title)
    t0 = time.perf_counter()
    cur.execute(stmt)
    if cur.description:
        for row in cur.fetchmany(40):
            print("  " + " | ".join(str(v) for v in row))
    else:
        print("  OK")
    print(f"  [{round((time.perf_counter() - t0) * 1000)} ms]")
