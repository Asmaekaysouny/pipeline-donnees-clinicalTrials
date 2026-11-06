"""Ingestion asynchrone de ClinicalTrials.gov (API v2) vers data/raw/ en JSON Lines.

Une collecte = plusieurs flux indépendants (un par année de début d'étude).
Dans un flux, la pagination par pageToken est séquentielle ; les flux avancent en parallèle.
Chaque flux a son checkpoint, ce qui permet de reprendre après une interruption.
"""
import argparse
import asyncio
import json
import os
import random
import time
from pathlib import Path

import aiohttp

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 1000
MAX_RETRIES = 6

# Champs du contrat de données (les e-mails de contact ne sont donc jamais demandés)
FIELDS = "|".join([
    "NCTId", "BriefTitle", "OverallStatus", "StudyType", "Phase",
    "StartDate", "CompletionDate", "EnrollmentCount", "Condition",
    "LeadSponsorName", "LeadSponsorClass", "LocationCountry",
    "MinimumAge", "Sex", "HasResults",
])


def build_streams():
    streams = {"avant_2000": "AREA[StartDate]RANGE[MIN,1999-12-31]"}
    for y in range(2000, 2027):
        streams[f"y{y}"] = f"AREA[StartDate]RANGE[{y}-01-01,{y}-12-31]"
    streams["apres_2026"] = "AREA[StartDate]RANGE[2027-01-01,MAX]"
    streams["sans_date"] = "NOT AREA[StartDate]RANGE[MIN,MAX]"
    return streams


def load_checkpoint(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"next_page_token": None, "pages": 0, "studies": 0, "done": False}


def save_checkpoint(path: Path, cp: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cp), encoding="utf-8")
    os.replace(tmp, path)  # écriture atomique


async def fetch_json(session, sem, params, stats):
    """GET avec sémaphore, timeout (défini sur la session) et retry à backoff exponentiel."""
    for attempt in range(MAX_RETRIES):
        try:
            async with sem:
                stats["requests"] += 1
                async with session.get(BASE_URL, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    if resp.status == 429 or resp.status >= 500:
                        retry_after = resp.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else 2 ** attempt
                    else:
                        raise RuntimeError(f"HTTP {resp.status} : {await resp.text()}")
        except (aiohttp.ClientError, asyncio.TimeoutError):
            delay = 2 ** attempt
        stats["retries"] += 1
        await asyncio.sleep(delay + random.random())
    raise RuntimeError(f"Échec après {MAX_RETRIES} tentatives : {params}")


async def ingest_stream(session, sem, raw_dir, name, flt, max_pages, stats):
    out_dir = raw_dir / name
    out_dir.mkdir(parents=True, exist_ok=True)
    cp_path = out_dir / "_checkpoint.json"
    cp = load_checkpoint(cp_path)
    if cp["done"]:
        return

    while True:
        params = {"pageSize": PAGE_SIZE, "fields": FIELDS,
                  "filter.advanced": flt, "format": "json"}
        if cp["next_page_token"]:
            params["pageToken"] = cp["next_page_token"]

        data = await fetch_json(session, sem, params, stats)
        studies = data.get("studies", [])

        # Nom déterministe + écriture atomique : rejouer une page l'écrase à l'identique
        page_file = out_dir / f"page_{cp['pages']:05d}.jsonl"
        tmp = page_file.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for s in studies:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        os.replace(tmp, page_file)

        # Le checkpoint n'avance qu'une fois la page écrite
        cp["pages"] += 1
        cp["studies"] += len(studies)
        cp["next_page_token"] = data.get("nextPageToken")
        cp["done"] = cp["next_page_token"] is None
        save_checkpoint(cp_path, cp)

        stats["pages"] += 1
        stats["studies"] += len(studies)
        if cp["done"] or (max_pages and cp["pages"] >= max_pages):
            break


async def main(args):
    streams = build_streams()
    if args.only:
        streams = {k: v for k, v in streams.items() if k in args.only}

    stats = {"requests": 0, "retries": 0, "pages": 0, "studies": 0}
    sem = asyncio.Semaphore(args.concurrency)
    timeout = aiohttp.ClientTimeout(total=60)
    headers = {"User-Agent": "pipeline-donnees-clinicaltrials/1.0"}
    raw_dir = Path(args.raw_dir)

    start = time.perf_counter()
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        await asyncio.gather(*(
            ingest_stream(session, sem, raw_dir, n, f, args.max_pages, stats)
            for n, f in streams.items()
        ))
    stats["duree_s"] = round(time.perf_counter() - start, 1)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--concurrency", type=int, default=5, help="requêtes simultanées max")
    p.add_argument("--max-pages", type=int, default=0, help="limite de pages par flux (0 = tout)")
    p.add_argument("--only", nargs="*", help="noms de flux, ex. y2020 y2021")
    p.add_argument("--raw-dir", default="data/raw")
    asyncio.run(main(p.parse_args()))
