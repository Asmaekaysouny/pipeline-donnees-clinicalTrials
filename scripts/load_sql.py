
import argparse
import os
import time
from pathlib import Path

import pyarrow.parquet as pq
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


def insert_values(cur, query, values):
    """Insère plusieurs lignes en une seule opération."""
    if values:
        execute_values(cur, query, values, page_size=1000)


def load_batch(cur, rows):
    """Charge un lot d'études et leurs relations."""

    # 1. Préparer les données de référence
    sponsors = {}
    conditions = set()
    countries = set()

    for row in rows:
        if row.get("sponsor"):
            sponsors[row["sponsor"]] = row.get("sponsor_class")

        conditions.update(row.get("conditions") or [])
        countries.update(row.get("countries") or [])

    # 2. Insérer les sponsors
    insert_values(
        cur,
        """
        INSERT INTO sponsors (name, class)
        VALUES %s
        ON CONFLICT (name) DO NOTHING
        """,
        list(sponsors.items())
    )

    # 3. Insérer les conditions
    insert_values(
        cur,
        """
        INSERT INTO conditions (name)
        VALUES %s
        ON CONFLICT (name) DO NOTHING
        """,
        [(condition,) for condition in conditions]
    )

    # 4. Insérer les pays
    insert_values(
        cur,
        """
        INSERT INTO countries (name)
        VALUES %s
        ON CONFLICT (name) DO NOTHING
        """,
        [(country,) for country in countries]
    )

    # 5. Récupérer les identifiants
    sponsor_ids = {}
    if sponsors:
        cur.execute(
            "SELECT sponsor_id, name FROM sponsors WHERE name = ANY(%s)",
            (list(sponsors.keys()),)
        )
        sponsor_ids = {name: sponsor_id for sponsor_id, name in cur.fetchall()}

    condition_ids = {}
    if conditions:
        cur.execute(
            "SELECT condition_id, name FROM conditions WHERE name = ANY(%s)",
            (list(conditions),)
        )
        condition_ids = {name: condition_id for condition_id, name in cur.fetchall()}

    country_ids = {}
    if countries:
        cur.execute(
            "SELECT country_id, name FROM countries WHERE name = ANY(%s)",
            (list(countries),)
        )
        country_ids = {name: country_id for country_id, name in cur.fetchall()}

    # 6. Préparer les études et les relations
    studies = []
    phases = set()
    study_conditions = set()
    study_countries = set()

    for row in rows:
        nct_id = row["nct_id"]

        sponsor_id = sponsor_ids.get(row.get("sponsor"))

        studies.append((
            nct_id,
            row.get("title"),
            row.get("status"),
            row.get("study_type"),
            row.get("start_date"),
            row.get("completion_date"),
            row.get("enrollment"),
            sponsor_id,
            row.get("min_age_years"),
            row.get("sex"),
            row.get("has_results")
        ))

        for phase in row.get("phases") or []:
            phases.add((nct_id, phase))

        for condition in row.get("conditions") or []:
            condition_id = condition_ids.get(condition)
            if condition_id is not None:
                study_conditions.add((nct_id, condition_id))

        for country in row.get("countries") or []:
            country_id = country_ids.get(country)
            if country_id is not None:
                study_countries.add((nct_id, country_id))

    # 7. Insérer les études
    insert_values(
        cur,
        """
        INSERT INTO studies (
            nct_id, title, status, study_type,
            start_date, completion_date, enrollment,
            sponsor_id, min_age_years, sex, has_results
        )
        VALUES %s
        ON CONFLICT (nct_id) DO NOTHING
        """,
        studies
    )

    # 8. Insérer les phases
    insert_values(
        cur,
        """
        INSERT INTO study_phases (nct_id, phase)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        list(phases)
    )

    # 9. Insérer les associations études-conditions
    insert_values(
        cur,
        """
        INSERT INTO study_conditions (nct_id, condition_id)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        list(study_conditions)
    )

    # 10. Insérer les associations études-pays
    insert_values(
        cur,
        """
        INSERT INTO study_countries (nct_id, country_id)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        list(study_countries)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Chargement des données ClinicalTrials.gov dans PostgreSQL"
    )
    parser.add_argument(
        "--input",
        default="data/processed/studies.parquet",
        help="Chemin du fichier Parquet"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2000,
        help="Nombre d'études chargées par lot"
    )
    args = parser.parse_args()

    load_dotenv()

    required_vars = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD"
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(
            f"Variables manquantes dans le fichier .env : {', '.join(missing)}"
        )

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {input_path}")

    parquet = pq.ParquetFile(input_path)
    total = parquet.metadata.num_rows

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    processed = 0
    start = time.perf_counter()

    try:
        with conn.cursor() as cur:
            for batch in parquet.iter_batches(
                batch_size=args.batch_size
            ):
                rows = batch.to_pylist()

                try:
                    load_batch(cur, rows)
                    conn.commit()

                except Exception:
                    conn.rollback()
                    raise

                processed += len(rows)

                print(
                    f"Progression : {processed}/{total} études",
                    flush=True
                )

        duration = round(time.perf_counter() - start, 2)

        print("\n=== Résultat du chargement ===")
        print(f"Études parcourues : {processed}")
        print(f"Durée : {duration} secondes")

        # Vérifier le nombre de lignes dans chaque table
        tables = [
            "sponsors",
            "studies",
            "study_phases",
            "conditions",
            "study_conditions",
            "countries",
            "study_countries"
        ]

        with conn.cursor() as cur:
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"{table} : {count} lignes")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
