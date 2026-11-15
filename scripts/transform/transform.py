"""Transformation : data/raw/**/*_page_*.jsonl -> data/processed/studies.parquet

Lecture par lots (une page à la fois), nettoyage et typage selon docs/contrat_donnees.md.
Seul l'ensemble des nct_id déjà vus est gardé en mémoire (déduplication).
"""
import argparse
import json
import os
import re
import time
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA = pa.schema([
    ("nct_id", pa.string()),
    ("title", pa.string()),
    ("status", pa.string()),
    ("study_type", pa.string()),
    ("phases", pa.list_(pa.string())),
    ("start_date", pa.date32()),
    ("completion_date", pa.date32()),
    ("enrollment", pa.int64()),
    ("conditions", pa.list_(pa.string())),
    ("sponsor", pa.string()),
    ("sponsor_class", pa.string()),
    ("countries", pa.list_(pa.string())),
    ("min_age_years", pa.int32()),
    ("sex", pa.string()),
    ("has_results", pa.bool_()),
])

_DATE_RE = re.compile(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?")
_AGE_RE = re.compile(r"\s*(\d+)\s*([A-Za-z]+)\s*")


def clean_text(value):
    """Texte nettoyé, ou None si vide / absent / pas une chaîne."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def parse_date(value):
    """'2020-03' -> 2020-03-01 ; '2020' -> 2020-01-01 ; date complète conservée ; sinon None."""
    value = clean_text(value)
    if not value:
        return None
    m = _DATE_RE.fullmatch(value)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2) or 1)
    day = int(m.group(3)) if m.group(3) else 1
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_min_age(value):
    """'18 Years' -> 18 ; '6 Months' -> 0 ; '24 Months' -> 2 ; 'N/A' ou absent -> None."""
    value = clean_text(value)
    if not value:
        return None
    m = _AGE_RE.fullmatch(value)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower().rstrip("s")
    if unit == "year":
        return n
    if unit == "month":
        return n // 12
    if unit in {"week", "day", "hour", "minute"}:
        return 0
    return None


def _text_list(values):
    return [t for v in (values or []) if (t := clean_text(v))]


def flatten_study(study):
    """Aplatit une étude JSON selon le contrat. Renvoie None si nct_id ou titre manquant."""
    p = study.get("protocolSection") or {}
    ident = p.get("identificationModule") or {}
    nct_id = clean_text(ident.get("nctId"))
    title = clean_text(ident.get("briefTitle"))
    if not nct_id or not title:
        return None

    status = p.get("statusModule") or {}
    design = p.get("designModule") or {}
    sponsor = (p.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
    elig = p.get("eligibilityModule") or {}
    locations = (p.get("contactsLocationsModule") or {}).get("locations") or []

    count = (design.get("enrollmentInfo") or {}).get("count")
    enrollment = count if isinstance(count, int) and not isinstance(count, bool) and count >= 0 else None

    return {
        "nct_id": nct_id,
        "title": title,
        "status": clean_text(status.get("overallStatus")),
        "study_type": clean_text(design.get("studyType")),
        "phases": _text_list(design.get("phases")),
        "start_date": parse_date((status.get("startDateStruct") or {}).get("date")),
        "completion_date": parse_date((status.get("completionDateStruct") or {}).get("date")),
        "enrollment": enrollment,
        "conditions": _text_list((p.get("conditionsModule") or {}).get("conditions")),
        "sponsor": clean_text(sponsor.get("name")),
        "sponsor_class": clean_text(sponsor.get("class")),
        "countries": sorted(set(_text_list(loc.get("country") for loc in locations))),
        "min_age_years": parse_min_age(elig.get("minimumAge")),
        "sex": clean_text(elig.get("sex")),
        "has_results": bool(study.get("hasResults", False)),
    }


def peak_memory_mb():
    """Pic de mémoire du processus (Mo). Nécessite psutil."""
    try:
        import psutil
        info = psutil.Process().memory_info()
        return round(getattr(info, "peak_wset", info.rss) / 1e6, 1)
    except ImportError:
        return None


def main(args):
    raw_dir = Path(args.raw_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".tmp")

    stats = {"fichiers": 0, "lignes_lues": 0, "gardees": 0,
             "ecartees_invalides": 0, "doublons": 0}
    seen = set()
    start = time.perf_counter()

    with pq.ParquetWriter(tmp_path, SCHEMA, compression="snappy") as writer:
        for page in sorted(raw_dir.glob("*_page_*.jsonl")):
            rows = []
            with page.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    stats["lignes_lues"] += 1
                    row = flatten_study(json.loads(line))
                    if row is None:
                        stats["ecartees_invalides"] += 1
                    elif row["nct_id"] in seen:
                        stats["doublons"] += 1
                    else:
                        seen.add(row["nct_id"])
                        rows.append(row)
            if rows:
                writer.write_table(pa.Table.from_pylist(rows, schema=SCHEMA))
            stats["fichiers"] += 1
            stats["gardees"] += len(rows)

    os.replace(tmp_path, out_path)
    stats["duree_s"] = round(time.perf_counter() - start, 1)
    stats["ram_max_mo"] = peak_memory_mb()
    stats["parquet_mo"] = round(out_path.stat().st_size / 1e6, 1)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--raw-dir", default="data/raw")
    p.add_argument("--out", default="data/processed/studies.parquet")
    main(p.parse_args())
