# Mesures et informations du projet

## Source et licence
- Source : ClinicalTrials.gov (NIH / National Library of Medicine, États-Unis), API v2
- Conditions d'utilisation : https://clinicaltrials.gov/about-site/terms-conditions
- Version des conditions : mise à jour le 31 janvier 2023 ; consultées le 2026-11-03
- Accès : gratuit, pour tous, y compris hors des États-Unis
- Licence : pas de licence standard (type CC0 ou CC-BY) ; ce sont des conditions d'utilisation propres au site
- Publication sur le Hub possible : oui, sous conditions

### Obligations en cas de publication ou de distribution
1. Citer ClinicalTrials.gov comme source des données
2. Garder les données à jour
3. Afficher clairement la date à laquelle ClinicalTrials.gov a traité les données
4. Décrire précisément toutes les modifications apportées aux données

### Interdictions
- Revendiquer des droits de propriété sur la base
- Présenter la base comme autre chose qu'une base de données du gouvernement américain
- Utiliser les adresses e-mail extraites à des fins de marketing ou de promotion

### Points de vigilance
- Certaines données peuvent relever du droit d'auteur de tiers (à signaler dans la Dataset Card)
- La base est mise à jour chaque jour : notre jeu de données est un instantané, daté
- Pas de reprise de la rubrique contacts (e-mails) dans notre jeu de données

## Modifications apportées aux données (à compléter au fil de la transformation)
- Dates partielles complétées au 1er du mois (ex. 2021-03 devient 2021-03-01)
- Âge minimal converti en nombre d'années entières
- Listes (conditions, pays, phases) dédupliquées et triées
- Doublons sur l'identifiant NCT supprimés
- Études sans identifiant ou sans titre écartées
- Date de traitement des données par ClinicalTrials.gov : remplie à la collecte complète (champ data_timestamp de data/raw/_manifest.json)

## Transformation
- Durée :
- RAM maximale :
- Lignes en entrée :
- Lignes en sortie :

## Base SQL
- Temps avant index :
- Temps après index :

## API (mesuré le 2026-11-03 à 14h25)
- Études dans toute la base : 610 050
- Études "breast cancer" : 16 983
- pageSize maximal : 1000 (au-delà, tronqué sans erreur)
- Durée d'une page de 10 / 100 / 1000 études : 0,39 s / 0,84 s / 1,86 s
- Poids moyen d'une étude : environ 19 ko
- Volume brut estimé : environ 11,7 Go pour toute la base, environ 325 Mo pour "breast cancer"
- Chaque requête a un coût fixe d'environ 0,3 à 0,4 s : d'où le choix de pageSize=1000
- La base grandit en continu : 16 983 études "breast cancer" le 03/11, 16 995 le 06/11

## Partitionnement (mesuré le 2026-11-06)

| | Par statut | Par année de début |
| --- | --- | --- |
| Partitions | 14 | 30 |
| Requêtes au total | 26 | 35 |
| Partition la plus lente | COMPLETED (7 787 études, 8 pages) | 2022 à 2026 (environ 1 000 à 1 100 études, 2 pages) |
| Somme = total (16 995) | OK | OK |

Choix : par année de début (+ avant 2000, après 2026, sans date).
- Partitions équilibrées : 2 pages au maximum, contre 8 pour COMPLETED (46 % des études).
- La date de début ne change pas pendant la collecte, contrairement au statut.

## Ingestion
- Date de traitement des données par ClinicalTrials.gov :
- Durée de la collecte complète : 6,04 s (concurrence 8), mesuré le 12/11/2026 
- Nombre de requêtes : 35
- Nombre d'études collectées : 17009
- Volume de data/raw/ : 376 Mo (35 fichiers)
- Nombre de retries :
- Durée en séquentiel (concurrence 1, collecte complète) : 28,49 s
- Gain de l'asynchrone : environ 4,7 fois plus rapide (28,49 s → 6,04 s)
