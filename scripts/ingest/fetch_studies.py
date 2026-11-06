"""Ingestion asynchrone des études ClinicalTrials.gov.

Brique B2 : pagination d'une partition et écriture en JSON Lines.
"""
from __future__ import annotations

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
    session: aiohttp.ClientSession, partition: str, page_token: str | None = None
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
    async with session.get(BASE_URL, params=params) as reponse:
        reponse.raise_for_status()
        return await reponse.json()


async def collecter_partition(session: aiohttp.ClientSession, partition: str) -> int:
    """Suit les jetons d'une partition jusqu'à la dernière page. Renvoie le nombre d'études."""
    numero = 1
    page_token = None
    total = 0
    while True:
        donnees = await recuperer_page(session, partition, page_token)
        etudes = donnees["studies"]
        chemin = nom_fichier(partition, numero)
        ecrire_page(chemin, etudes)
        total += len(etudes)
        print(f"  {chemin.name} : {len(etudes)} études")
        page_token = donnees.get("nextPageToken")
        if not page_token:
            return total
        numero += 1


async def main() -> None:
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        for partition in ("2025", "2020"):
            debut = time.perf_counter()
            total = await collecter_partition(session, partition)
            duree = time.perf_counter() - debut
            print(f"{partition} : {total} études en {duree:.2f} s")


if __name__ == "__main__":
    asyncio.run(main())