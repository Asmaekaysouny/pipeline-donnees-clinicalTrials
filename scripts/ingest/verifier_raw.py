"""Vérifie les fichiers bruts : nombre d'études, doublons et trous dans les pages."""
import json
import re
from collections import defaultdict
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

fichiers = sorted(RAW_DIR.glob("*_page_*.jsonl"))
identifiants = []
pages = defaultdict(list)
for fichier in fichiers:
    partition, numero = re.match(r"(.+)_page_(\d+)\.jsonl", fichier.name).groups()
    pages[partition].append(int(numero))
    with fichier.open(encoding="utf-8") as lignes:
        for ligne in lignes:
            etude = json.loads(ligne)
            identifiants.append(etude["protocolSection"]["identificationModule"]["nctId"])

trous = {p: n for p, n in pages.items() if sorted(n) != list(range(1, len(n) + 1))}
doublons = len(identifiants) - len(set(identifiants))
print(f"Fichiers    : {len(fichiers)} ({len(pages)} partitions)")
print(f"Études      : {len(identifiants)}")
print(f"nctId uniques : {len(set(identifiants))} -> doublons : {doublons}")
print(f"Pages manquantes : {trous if trous else 'aucune'}")