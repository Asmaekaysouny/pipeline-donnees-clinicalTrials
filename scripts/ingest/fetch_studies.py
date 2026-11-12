"""Ingestion asynchrone des études ClinicalTrials.gov.

Brique B3 : toutes les partitions en parallèle, limitées par un sémaphore.
Usage : python scripts/ingest/fetch_studies.py --concurrence 8
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import aiohttp

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
CONDITION = "breast cancer"
PAGE_SIZE = 1000
TIMEOUT = aiohttp.ClientTimeout(total=60)
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PARTITIONS = (
    ["avant_2000"]
    + [str(annee) for annee in range(2000, 2027)]
    + ["apres_2026", "sans_date"]
)


def filtre_partition(partition: str) -> str:
    """Traduit un nom de partition en filtre de date de début pour l'API."""
    if partition == "avant_2000":
        return "AREA[StartDate]RANGE[MIN,1999-12-31]"
    if partition == "apres_2026":
        return "AREA[StartDate]RANGE[2027-01-01,MAX]"
    if partition == "sans_date":
        return "AREA[StartDate]MISSING"
    return f"AREA[StartDate]RANGE[{partition}-01-01,{partition}-12-31]"


def nom_fichier(partition: str, numero: int) -> Path:
    """Chemin déterministe d'une page : data/raw/2025_page_00001.jsonl."""
    return RAW_DIR / f"{partition}_page_{numero:05d}.jsonl"


def ecrire_page(chemin: Path, etudes: list[dict]) -> None:
    """Écrit une étude par ligne, via un fichier temporaire renommé à la fin."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(".jsonl.tmp")
    with temporaire.open("w", encoding="utf-8") as fichier:
        for etude in etudes:
            fichier.write(json.dumps(etude, ensure_ascii=False) + "\n")
    os.replace(temporaire, chemin)


async def recuperer_page(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    partition: str,
    page_token: str | None = None,
) -> dict:
    """Demande une page d'études d'une partition et renvoie le JSON décodé."""
    params = {
        "query.cond": CONDITION,
        "query.term": filtre_partition(partition),
        "pageSize": PAGE_SIZE,
        "countTotal": "true",
    }
    if page_token:
        params["pageToken"] = page_token
    async with semaphore:
        async with session.get(BASE_URL, params=params) as reponse:
            reponse.raise_for_status()
            return await reponse.json()


async def collecter_partition(
    session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, partition: str
) -> dict:
    """Suit les jetons d'une partition jusqu'à la dernière page."""
    numero = 1
    page_token = None
    etudes_recues = 0
    attendu = 0
    while True:
        donnees = await recuperer_page(session, semaphore, partition, page_token)
        if numero == 1:
            attendu = donnees.get("totalCount", 0)
        etudes = donnees["studies"]
        ecrire_page(nom_fichier(partition, numero), etudes)
        etudes_recues += len(etudes)
        page_token = donnees.get("nextPageToken")
        if not page_token:
            print(f"  {partition:<11} {etudes_recues:>5} études, {numero} page(s)")
            return {"partition": partition, "etudes": etudes_recues,
                    "attendu": attendu, "pages": numero}
        numero += 1


async def main(concurrence: int) -> None:
    semaphore = asyncio.Semaphore(concurrence)
    debut = time.perf_counter()
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        resultats = await asyncio.gather(
            *(collecter_partition(session, semaphore, p) for p in PARTITIONS)
        )
    duree = time.perf_counter() - debut

    etudes = sum(r["etudes"] for r in resultats)
    attendu = sum(r["attendu"] for r in resultats)
    pages = sum(r["pages"] for r in resultats)
    print(f"\nConcurrence : {concurrence}")
    print(f"Partitions  : {len(resultats)}")
    print(f"Requêtes    : {pages}")
    print(f"Études      : {etudes} (attendu {attendu}) -> {'OK' if etudes == attendu else 'ÉCART'}")
    print(f"Durée       : {duree:.2f} s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestion ClinicalTrials.gov")
    parser.add_argument("--concurrence", type=int, default=8,
                        help="nombre maximal de requêtes simultanées")
    args = parser.parse_args()
    asyncio.run(main(args.concurrence))