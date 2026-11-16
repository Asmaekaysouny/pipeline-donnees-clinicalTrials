"""Publication sur le Hugging Face Hub : Parquet + Dataset Card, dépôt privé par défaut.

Le jeton est lu dans la variable d'environnement HF_TOKEN (fichier .env, jamais versionné).
"""
import argparse
import os
import sys
from pathlib import Path

import pyarrow.parquet as pq
from dotenv import load_dotenv
from huggingface_hub import HfApi


def build_card(card_path, nb_etudes, date_collecte):
    card = Path(card_path).read_text(encoding="utf-8-sig")
    card = card.replace("{{NB_ETUDES}}", f"{nb_etudes:,}".replace(",", " "))
    card = card.replace("{{DATE_COLLECTE}}", date_collecte)
    if "{{" in card:
        sys.exit("La carte contient encore des champs {{...}} non remplis.")
    return card


def main(args):
    load_dotenv(override=True)
    token = os.getenv("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN introuvable : ajoute-le dans le fichier .env.")

    parquet = Path(args.parquet)
    nb_etudes = pq.ParquetFile(parquet).metadata.num_rows
    if nb_etudes < 100_000:
        sys.exit(f"Parquet suspect : {nb_etudes} lignes. Publication annulée.")
    card = build_card(args.card, nb_etudes, args.date_collecte)

    api = HfApi(token=token)
    api.create_repo(args.repo, repo_type="dataset", private=True, exist_ok=True)
    api.upload_file(
        path_or_fileobj=str(parquet), path_in_repo="data/studies.parquet",
        repo_id=args.repo, repo_type="dataset", commit_message="Ajout du fichier Parquet",
    )
    api.upload_file(
        path_or_fileobj=card.encode("utf-8"), path_in_repo="README.md",
        repo_id=args.repo, repo_type="dataset", commit_message="Ajout de la Dataset Card",
    )
    if args.public:
        api.update_repo_settings(args.repo, repo_type="dataset", private=False)
    if args.tag:
        api.create_tag(args.repo, tag=args.tag, repo_type="dataset", exist_ok=True)

    print(f"{nb_etudes} études publiées : https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default="Asmae04/clinicaltrials-studies")
    p.add_argument("--parquet", default="data/processed/studies.parquet")
    p.add_argument("--card", default="docs/dataset_card.md")
    p.add_argument("--date-collecte", required=True, help="AAAA-MM-JJ")
    p.add_argument("--public", action="store_true", help="rend le dépôt public")
    p.add_argument("--tag", help="ex. v1.0.0")
    main(p.parse_args())

