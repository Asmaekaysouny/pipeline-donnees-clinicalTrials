"""Exploration de l'API ClinicalTrials.gov v2.

Mesure : nombre total d'études, taille de page maximale,
temps de réponse et poids d'une page selon sa taille.
Script synchrone et sans dépendance : il sert à décider, pas à collecter.
"""
import json
import time
import urllib.parse
import urllib.request

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
CONDITION = "breast cancer"


def appeler(params):
    """Fait un appel GET et renvoie (json, taille en octets, durée en secondes)."""
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    debut = time.perf_counter()
    with urllib.request.urlopen(url, timeout=60) as reponse:
        brut = reponse.read()
    duree = time.perf_counter() - debut
    return json.loads(brut), len(brut), duree


# 1. Volume total
donnees, _, _ = appeler({"pageSize": 1, "countTotal": "true"})
total_global = donnees["totalCount"]
donnees, _, _ = appeler({"pageSize": 1, "countTotal": "true", "query.cond": CONDITION})
total_condition = donnees["totalCount"]
print(f"Études dans toute la base : {total_global}")
print(f"Études '{CONDITION}'      : {total_condition}")

# 2. Taille de page maximale : on demande plus que le maximum supposé
donnees, _, _ = appeler({"pageSize": 1500, "query.cond": CONDITION})
print(f"\npageSize=1500 demandé -> {len(donnees['studies'])} études reçues")

# 3. Temps de réponse et poids selon la taille de page
print(f"\n{'pageSize':>8} | {'durée (s)':>9} | {'taille (Mo)':>11} | {'ko/étude':>8}")
for taille in (10, 100, 1000):
    donnees, octets, duree = appeler({"pageSize": taille, "query.cond": CONDITION})
    n = len(donnees["studies"])
    print(f"{taille:>8} | {duree:>9.2f} | {octets / 1e6:>11.2f} | {octets / n / 1e3:>8.1f}")

# 4. Estimation du volume brut à collecter
ko_par_etude = octets / n / 1e3
print(f"\nVolume brut estimé, toute la base : {total_global * ko_par_etude / 1e6:.1f} Go")
print(f"Volume brut estimé, '{CONDITION}' : {total_condition * ko_par_etude / 1e3:.0f} Mo")
print(f"Requêtes nécessaires à 1000/page  : {-(-total_condition // 1000)}")