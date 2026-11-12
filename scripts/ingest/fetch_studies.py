"""Ingestion asynchrone des études ClinicalTrials.gov.

ETAPE 6 : manifeste de la collecte et date de traitement des données.
Usage : python scripts/ingest/fetch_studies.py --concurrence 8
Test  : python scripts/ingest/fetch_studies.py --taux-echec 0.3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import time
from datetime import datetime
from pathlib import Path

import aiohttp

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
VERSION_URL= "https://clinicaltrials.gov/api/v2/version"
CONDITION = "breast cancer"
PAGE_SIZE = 1000
TIMEOUT = aiohttp.ClientTimeout(total=60)
RACINE = Path(__file__).resolve().parents[2]
RAW_DIR = RACINE / "data" / "raw"
CHECKPOINT = RACINE / "checkpoint.json"
MANIFESTE = RAW_DIR / "_manifest.json"
PARTITIONS = (
    ["avant_2000"]
    + [str(annee) for annee in range(2000, 2027)]
    + ["apres_2026", "sans_date"]
)

MAX_TENTATIVES = 5
DELAI_BASE = 1.0
CODES_TEMPORAIRES = {429, 500, 502, 503, 504}
STATS = {"tentatives": 0, "retries": 0}


class ErreurTemporaire(Exception):
    """Erreur qui vaut la peine d'être retentée (serveur saturé, panne passagère)."""


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


def ecrire_json_atomique(chemin: Path, contenu: dict) -> None:
    """Écrit un fichier JSON via un fichier temporaire renommé à la fin."""
    temporaire = chemin.with_suffix(".json.tmp")
    temporaire.write_text(json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporaire, chemin)


def charger_checkpoint() -> dict:
    """Renvoie l'état sauvegardé de chaque partition, ou un dictionnaire vide."""
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    return {}


def nettoyer_raw() -> None:
    """Supprime les pages d'une ancienne collecte avant d'en commencer une nouvelle."""
    for fichier in list(RAW_DIR.glob("*_page_*.jsonl")) + list(RAW_DIR.glob("*.tmp")):
        fichier.unlink()
    if MANIFESTE.exists():
        MANIFESTE.unlink()


async def lire_version(session: aiohttp.ClientSession) -> dict:
    """Renvoie la version de l'API et la date de traitement des données (dataTimestamp)."""
    async with session.get(VERSION_URL) as reponse:
        reponse.raise_for_status()
        return await reponse.json(content_type=None)


def delai_attente(tentative: int) -> float:
    """Attente exponentielle : 1 s, 2 s, 4 s, 8 s, plus un peu d'aléatoire (jitter)."""
    return DELAI_BASE * 2 ** (tentative - 1) + random.uniform(0, 0.5)


async def requete_api(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    params: dict,
    taux_echec: float,
) -> dict:
    """Fait la requête, et la retente en cas d'erreur temporaire."""
    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            async with semaphore:
                STATS["tentatives"] += 1
                if random.random() < taux_echec:
                    raise ErreurTemporaire("erreur simulée")
                async with session.get(BASE_URL, params=params) as reponse:
                    if reponse.status in CODES_TEMPORAIRES:
                        raise ErreurTemporaire(f"HTTP {reponse.status}")
                    reponse.raise_for_status()
                    return await reponse.json()
        except (ErreurTemporaire, aiohttp.ClientConnectionError, asyncio.TimeoutError) as erreur:
            if tentative == MAX_TENTATIVES:
                raise
            attente = delai_attente(tentative)
            STATS["retries"] += 1
            print(f"    nouvelle tentative dans {attente:.1f} s ({erreur or type(erreur).__name__})")
            await asyncio.sleep(attente)
    raise RuntimeError("inatteignable")


async def recuperer_page(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    partition: str,
    page_token: str | None,
    taux_echec: float,
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
    return await requete_api(session, semaphore, params, taux_echec)


async def collecter_partition(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    partition: str,
    taux_echec: float,
    etat: dict,
) -> dict:
    """Suit les jetons d'une partition jusqu'à la dernière page, en reprenant si besoin."""
    sauvegarde = etat.get(partition)
    if sauvegarde and sauvegarde["statut"] == "terminee":
        print(f"  {partition:<11} déjà terminée, ignorée")
        return sauvegarde
    if sauvegarde:
        numero = sauvegarde["pages"] + 1
        page_token = sauvegarde["prochain_token"]
        etudes_recues = sauvegarde["etudes"]
        attendu = sauvegarde["attendu"]
        print(f"  {partition:<11} reprise à la page {numero}")
    else:
        numero, page_token, etudes_recues, attendu = 1, None, 0, 0

    while True:
        donnees = await recuperer_page(session, semaphore, partition, page_token, taux_echec)
        if numero == 1:
            attendu = donnees.get("totalCount", 0)
        etudes = donnees["studies"]
        ecrire_page(nom_fichier(partition, numero), etudes)
        etudes_recues += len(etudes)
        page_token = donnees.get("nextPageToken")
        etat[partition] = {
            "partition": partition,
            "statut": "en_cours" if page_token else "terminee",
            "pages": numero,
            "prochain_token": page_token,
            "etudes": etudes_recues,
            "attendu": attendu,
        }
        ecrire_json_atomique(CHECKPOINT, etat)
        if not page_token:
            print(f"  {partition:<11} {etudes_recues:>5} études, {numero} page(s)")
            return etat[partition]
        numero += 1


async def main(concurrence: int, taux_echec: float) -> None:
    etat = charger_checkpoint()
    debut = time.perf_counter()
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        if etat:
            terminees = sum(1 for p in PARTITIONS if etat.get(p, {}).get("statut") == "terminee")
            print(f"Reprise d'une collecte interrompue : {terminees} partition(s) déjà terminée(s)")
        else:
            nettoyer_raw()
            version = await lire_version(session)
            etat["_collecte"] = {
                "collecte_debut": datetime.now().astimezone().isoformat(timespec="seconds"),
                "data_timestamp": version["dataTimestamp"],
                "api_version": version["apiVersion"],
            }
            print(f"Nouvelle collecte (données traitées par ClinicalTrials.gov le {version['dataTimestamp']})")
        semaphore = asyncio.Semaphore(concurrence)
        resultats = await asyncio.gather(
            *(collecter_partition(session, semaphore, p, taux_echec, etat) for p in PARTITIONS)
        )
    duree = time.perf_counter() - debut

    etudes = sum(r["etudes"] for r in resultats)
    attendu = sum(r["attendu"] for r in resultats)
    pages = sum(r["pages"] for r in resultats)
    print(f"\nConcurrence : {concurrence}")
    print(f"Partitions  : {len(resultats)}")
    print(f"Pages       : {pages}")
    print(f"Tentatives  : {STATS['tentatives']} (dont {STATS['retries']} retries)")
    print(f"Études      : {etudes} (attendu {attendu}) -> {'OK' if etudes == attendu else 'ÉCART'}")
    print(f"Durée       : {duree:.2f} s")

    if etudes == attendu:
        manifeste = {
            "source": "ClinicalTrials.gov, API v2",
            "condition": CONDITION,
            **etat["_collecte"],
            "collecte_fin": datetime.now().astimezone().isoformat(timespec="seconds"),
            "partitions": {r["partition"]: r["etudes"] for r in resultats},
            "pages": pages,
            "total_attendu": attendu,
            "total_collecte": etudes,
        }
        ecrire_json_atomique(MANIFESTE, manifeste)
        CHECKPOINT.unlink()
        print(f"Collecte complète : manifeste écrit dans {MANIFESTE.name}, checkpoint supprimé")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestion ClinicalTrials.gov")
    parser.add_argument("--concurrence", type=int, default=8,
                        help="nombre maximal de requêtes simultanées")
    parser.add_argument("--taux-echec", type=float, default=0.0,
                        help="test : proportion de requêtes qui échouent volontairement (0 à 1)")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.concurrence, args.taux_echec))
    except KeyboardInterrupt:
        print("\nInterrompu. Relancez la même commande pour reprendre.")