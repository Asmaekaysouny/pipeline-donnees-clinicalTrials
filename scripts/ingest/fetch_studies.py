"""Ingestion asynchrone des études ClinicalTrials.gov.

Brique B1 : un seul appel asynchrone, pour une partition.
"""
from __future__ import annotations

import asyncio
import time

import aiohttp

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
CONDITION = "breast cancer"
PAGE_SIZE = 1000
TIMEOUT = aiohttp.ClientTimeout(total=60)


def filtre_partition(partition: str) -> str:
    """Traduit un nom de partition en filtre de date de début pour l'API."""
    if partition == "avant_2000":
        return "AREA[StartDate]RANGE[MIN,1999-12-31]"
    if partition == "apres_2026":
        return "AREA[StartDate]RANGE[2027-01-01,MAX]"
    if partition == "sans_date":
        return "AREA[StartDate]MISSING"
    return f"AREA[StartDate]RANGE[{partition}-01-01,{partition}-12-31]"


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


async def main() -> None:
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        for partition in ("2020", "2025"):
            debut = time.perf_counter()
            donnees = await recuperer_page(session, partition)
            duree = time.perf_counter() - debut
            print(
                f"{partition} : {donnees['totalCount']} études au total, "
                f"{len(donnees['studies'])} reçues en {duree:.2f} s, "
                f"page suivante : {'oui' if 'nextPageToken' in donnees else 'non'}"
            )


if __name__ == "__main__":
    asyncio.run(main())