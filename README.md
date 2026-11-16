# Pipeline de données : ClinicalTrials.gov

Pipeline complet de collecte, de transformation, de stockage SQL et de publication de 610 511 études cliniques issues de l'API v2 de ClinicalTrials.gov.

## Source et licence

- **Source** : ClinicalTrials.gov (U.S. National Library of Medicine, NIH), API v2 : https://clinicaltrials.gov/data-api/api
- **Licence** : pas de licence standard. Les conditions d'utilisation de ClinicalTrials.gov s'appliquent : https://clinicaltrials.gov/about-site/terms-conditions (citer la source, indiquer la date de traitement, décrire les modifications).
- Les coordonnées de contact (e-mails) ne sont pas collectées.

## Architecture

```text
API ClinicalTrials.gov
   |  ingestion asynchrone (aiohttp, 29 flux par année de début, checkpoints)
   v
data/raw/*.jsonl          (brut, jamais modifié)
   |  transformation par lots (pyarrow)
   v
data/processed/studies.parquet
   |-- chargement idempotent --> PostgreSQL (7 tables) --> requêtes d'analyse
   '-- publication ------------> Hugging Face Hub (Dataset Card)
```

## Structure du dépôt

```text
sql/          schéma, requêtes d'analyse, index, scripts de mesure
scripts/
  ingest/       client.py (ingestion asynchrone), fetch_studies.py (version avec manifeste), verifier_raw.py
  transform/    transform.py (JSONL -> Parquet)
  load_db.py    chargement PostgreSQL
  run_sql.py    exécution de fichiers SQL
  publish_hub.py  publication sur le Hub
tests/        tests pytest de la transformation
docs/         contrat de données, Dataset Card
mesures.md    mesures de l'API et du partitionnement
```

`data/` et `.env` ne sont pas versionnés.

## Installation

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Il faut aussi un PostgreSQL local avec une base vide (par exemple `CREATE DATABASE clinicaltrials;`).

## Variables d'environnement (`.env`)

| Variable | Rôle |
|---|---|
| DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD | connexion PostgreSQL |
| HF_TOKEN | jeton Hugging Face en écriture (publication) |

## Lancer chaque étape

```text
python scripts/ingest/client.py --concurrency 5
python scripts/transform/transform.py
python scripts/load_db.py
python scripts/run_sql.py sql/requetes.sql
python scripts/run_sql.py sql/explain_index.sql
python scripts/run_sql.py sql/index.sql
python scripts/publish_hub.py --date-collecte AAAA-MM-JJ --tag v1.0.0
python -m pytest tests -v
```

- Ingestion : options `--only y2020 y2021`, `--max-pages`, `--raw-dir`. Après une interruption, relancer la même commande reprend à la page suivante de chaque flux.
- Une seconde version de l'ingestion, avec manifeste, se trouve dans `scripts/ingest/fetch_studies.py` (voir son en-tête et `mesures.md`).
- Le chargement SQL est idempotent : le relancer n'ajoute aucun doublon.
- `sql/requetes.sql` contient les 5 requêtes d'analyse du projet ; `sql/queries.sql` regroupe des requêtes complémentaires (par exemple études par statut, conditions les plus fréquentes).
- La transformation lit les fichiers bruts des deux ingestions (`data/raw/<flux>/page_*.jsonl` ou `data/raw/*_page_*.jsonl`). Le contrôle du total avec `_manifest.json` n'est actif qu'avec `fetch_studies.py` ; sinon le résumé indique « manifeste absent ».
- La publication refuse d'envoyer un Parquet de moins de 100 000 lignes.

## Résultats mesurés

| Étape | Mesure |
|---|---|
| Ingestion | 625 pages, 610 511 études, 0 retry |
| Séquentiel contre asynchrone (12 pages, 12 000 études) | 9,7 s contre 3,0 s, soit environ x3,2 |
| Collecte complète (dernière exécution, 615 pages) | 104,6 s en concurrence 5 |
| Reprise après interruption | aucun doublon |
| Transformation | 26,0 s, RAM maximale 178,3 Mo, Parquet de 72 Mo |
| Chargement PostgreSQL (base vide) | 201,1 s |
| Index `study_conditions(condition_id)` | médiane 174,5 ms puis 79,2 ms, soit environ x2,2 (3 mesures par état) |
| Tests | 12 tests pytest |

Tables PostgreSQL : studies 610 511, sponsors 52 715, conditions 135 219, countries 226, study_conditions 1 099 908, study_countries 789 736, study_phases 490 571.

## Jeu de données publié

Hugging Face Hub : https://huggingface.co/datasets/Asmae04/clinicaltrials-studies (version v1.0.0). Le schéma, les modifications apportées et les limites sont décrits dans la Dataset Card (`docs/dataset_card.md`).

## Limites et pistes d'amélioration

- Instantané figé à la date de collecte, alors que la source est mise à jour chaque jour. Piste : mise à jour incrémentale.
- Dans un flux, la pagination est séquentielle (chaque page dépend du jeton de la précédente) : le gain vient de la parallélisation entre flux.
- Conditions en texte libre : des variantes d'un même terme sont comptées séparément. Piste : normalisation avec un vocabulaire contrôlé (MeSH).
- Sponsors masqués (`[Redacted]`) et dates partielles complétées au 1er du mois.
- `has_results` est biaisé à la baisse pour les études récentes.

## Équipe

Asmae Kaysouny et Majda Bashir (voir l'historique Git pour le détail des contributions).

