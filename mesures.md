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
- Date de traitement des données par ClinicalTrials.gov : (à noter)

## Transformation
- Durée :
- RAM maximale :
- Lignes en entrée :
- Lignes en sortie :

## Base SQL
- Temps avant index :
- Temps après index :