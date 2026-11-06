"""Comparaison de deux partitionnements pour l'ingestion :
par statut de l'essai, ou par année de début.

Pour chacun : nombre d'études par partition, nombre de pages
(à 1000 études par page), et vérification que la somme égale le total.
"""
import json
import math
import urllib.parse
import urllib.request

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
CONDITION = "breast cancer"
PAGE_SIZE = 1000

STATUTS = [
    "ACTIVE_NOT_RECRUITING", "COMPLETED", "ENROLLING_BY_INVITATION",
    "NOT_YET_RECRUITING", "RECRUITING", "SUSPENDED", "TERMINATED",
    "WITHDRAWN", "AVAILABLE", "NO_LONGER_AVAILABLE",
    "TEMPORARILY_NOT_AVAILABLE", "APPROVED_FOR_MARKETING", "WITHHELD", "UNKNOWN",
]


def compter(**filtres):
    """Renvoie le nombre d'études pour la pathologie, avec des filtres en plus."""
    params = {"query.cond": CONDITION, "pageSize": 1, "countTotal": "true", **filtres}
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as reponse:
        return json.load(reponse)["totalCount"]


def resumer(nom, partitions, total):
    """Affiche le bilan d'un partitionnement."""
    pages = {p: math.ceil(n / PAGE_SIZE) for p, n in partitions.items()}
    somme = sum(partitions.values())
    pire = max(pages, key=pages.get)
    print(f"\n=== {nom} ===")
    print(f"Partitions              : {len(partitions)}")
    print(f"Requêtes au total       : {sum(pages.values())}")
    print(f"Partition la plus lente : {pire} ({partitions[pire]} études, {pages[pire]} pages)")
    print(f"Somme des partitions    : {somme} / total {total} -> {'OK' if somme == total else 'ÉCART'}")


total = compter()
print(f"Total '{CONDITION}' : {total}")

# Partitionnement 1 : par statut
par_statut = {s: compter(**{"filter.overallStatus": s}) for s in STATUTS}
for s, n in par_statut.items():
    print(f"  {s:<28} {n}")
resumer("Par statut", par_statut, total)

# Partitionnement 2 : par année de début
par_annee = {"avant_2000": compter(**{"query.term": "AREA[StartDate]RANGE[MIN,1999-12-31]"})}
for annee in range(2000, 2027):
    par_annee[str(annee)] = compter(**{"query.term": f"AREA[StartDate]RANGE[{annee}-01-01,{annee}-12-31]"})
par_annee["apres_2026"] = compter(**{"query.term": "AREA[StartDate]RANGE[2027-01-01,MAX]"})
par_annee["sans_date"] = compter(**{"query.term": "AREA[StartDate]MISSING"})
for p, n in par_annee.items():
    print(f"  {p:<12} {n}")
resumer("Par année de début", par_annee, total)