"""Chargement idempotent d'un fichier Parquet dans PostgreSQL (schéma sql/schema.sql)."""
import argparse
import json
import os
import time
from pathlib import Path

import psycopg2
import pyarrow.parquet as pq
from dotenv import load_dotenv
from psycopg2.extras import execute_values

COLUMNS = [
    "nct_id", "title", "status", "study_type", "phases", "start_date",
    "completion_date", "enrollment", "conditions", "sponsor", "sponsor_class",
    "countries", "min_age_years", "sex", "has_results",
]
TABLES = ["sponsors", "studies", "study_phases", "conditions",
          "study_conditions", "countries", "study_countries"]


def connect():
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def count(cur, table):
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def ensure_ids(cur, table, id_col, names, cache, extra_col=None, extra=None):
    """Insère les nouveaux noms (ON CONFLICT DO NOTHING) puis remplit le cache nom -> id."""
    new = [n for n in names if n not in cache]
    if not new:
        return
    if extra_col:
        execute_values(
            cur,
            f"INSERT INTO {table} (name, {extra_col}) VALUES %s ON CONFLICT (name) DO NOTHING",
            [(n, extra.get(n)) for n in new],
        )
    else:
        execute_values(
            cur,
            f"INSERT INTO {table} (name) VALUES %s ON CONFLICT (name) DO NOTHING",
            [(n,) for n in new],
        )
    cur.execute(f"SELECT name, {id_col} FROM {table} WHERE name = ANY(%s)", (new,))
    cache.update(dict(cur.fetchall()))


def load_batch(cur, rows, caches):
    sponsors = {r["sponsor"]: r["sponsor_class"] for r in rows if r["sponsor"]}
    ensure_ids(cur, "sponsors", "sponsor_id", list(sponsors), caches["sponsors"],
               "class", sponsors)
    conditions = {c for r in rows for c in (r["conditions"] or [])}
    ensure_ids(cur, "conditions", "condition_id", list(conditions), caches["conditions"])
    countries = {c for r in rows for c in (r["countries"] or [])}
    ensure_ids(cur, "countries", "country_id", list(countries), caches["countries"])

    studies = [
        (r["nct_id"], r["title"], r["status"], r["study_type"], r["start_date"],
         r["completion_date"], r["enrollment"], caches["sponsors"].get(r["sponsor"]),
         r["min_age_years"], r["sex"], bool(r["has_results"]))
        for r in rows
    ]
    execute_values(
        cur,
        "INSERT INTO studies (nct_id, title, status, study_type, start_date, "
        "completion_date, enrollment, sponsor_id, min_age_years, sex, has_results) "
        "VALUES %s ON CONFLICT (nct_id) DO NOTHING",
        studies, page_size=2000,
    )

    phases = [(r["nct_id"], p) for r in rows for p in set(r["phases"] or [])]
    if phases:
        execute_values(cur, "INSERT INTO study_phases (nct_id, phase) VALUES %s "
                            "ON CONFLICT DO NOTHING", phases, page_size=5000)
    links = [(r["nct_id"], caches["conditions"][c])
             for r in rows for c in set(r["conditions"] or [])]
    if links:
        execute_values(cur, "INSERT INTO study_conditions (nct_id, condition_id) VALUES %s "
                            "ON CONFLICT DO NOTHING", links, page_size=5000)
    links = [(r["nct_id"], caches["countries"][c])
             for r in rows for c in set(r["countries"] or [])]
    if links:
        execute_values(cur, "INSERT INTO study_countries (nct_id, country_id) VALUES %s "
                            "ON CONFLICT DO NOTHING", links, page_size=5000)


def main(args):
    conn = connect()
    cur = conn.cursor()
    cur.execute(Path(args.schema).read_text(encoding="utf-8-sig"))
    conn.commit()

    avant = count(cur, "studies")
    caches = {"sponsors": {}, "conditions": {}, "countries": {}}
    start = time.perf_counter()
    lues = 0

    pf = pq.ParquetFile(args.parquet)
    for i, batch in enumerate(pf.iter_batches(batch_size=args.batch_size, columns=COLUMNS)):
        rows = batch.to_pylist()
        load_batch(cur, rows, caches)
        conn.commit()  # un lot = une transaction
        lues += len(rows)
        if (i + 1) % 10 == 0:
            print(f"{lues} lignes traitées...", flush=True)

    stats = {"lignes_parquet": lues, "studies_avant": avant,
             "studies_apres": count(cur, "studies"),
             "duree_s": round(time.perf_counter() - start, 1)}
    stats["tables"] = {t: count(cur, t) for t in TABLES}
    print(json.dumps(stats, indent=2))
    conn.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--parquet", default="data/processed/studies.parquet")
    p.add_argument("--schema", default="sql/schema.sql")
    p.add_argument("--batch-size", type=int, default=10000)
    main(p.parse_args())
