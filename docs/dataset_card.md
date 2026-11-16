---
license: other
license_name: clinicaltrials-gov-terms
license_link: https://clinicaltrials.gov/about-site/terms-conditions
language:
- en
pretty_name: ClinicalTrials.gov - études cliniques (extrait structuré)
size_categories:
- 100K<n<1M
tags:
- clinical-trials
- medical
- tabular
configs:
- config_name: default
  data_files: data/studies.parquet
---

# ClinicalTrials.gov : études cliniques (extrait structuré)

## Description

Jeu de données tabulaire de {{NB_ETUDES}} études cliniques, issu de l'API v2 de ClinicalTrials.gov et nettoyé par un pipeline Python (ingestion asynchrone, transformation par lots, Parquet). Une ligne correspond à une étude. Les valeurs textuelles sont en anglais, comme dans la source.

## Source et attribution

- **Source** : ClinicalTrials.gov, base de données du gouvernement des États-Unis tenue par la National Library of Medicine (NIH).
- **Date de collecte et de traitement** : {{DATE_COLLECTE}}.
- Ce jeu est une copie dérivée réalisée dans un cadre pédagogique. Il n'est ni maintenu ni approuvé par la NLM, et ne remplace pas la base officielle, mise à jour chaque jour.

## Licence et conditions d'utilisation

Ces données ne sont pas sous une licence standard : les conditions d'utilisation de ClinicalTrials.gov s'appliquent (https://clinicaltrials.gov/about-site/terms-conditions). Elles demandent notamment de citer la source, d'indiquer la date de traitement et de décrire les modifications apportées. Certaines données peuvent relever du copyright de tiers. Consultez la version en vigueur de ces conditions avant toute réutilisation.

## Modifications apportées aux données

- Sélection de 15 champs parmi ceux de l'API, aplatissement du JSON imbriqué.
- Exclusion des coordonnées de contact (dont les e-mails).
- Dates partielles complétées au 1er du mois (« 2020-03 » devient 2020-03-01).
- Âge minimum converti en années entières (« 6 Months » devient 0, « 24 Months » devient 2) ; valeur vide si absent ou « N/A ».
- Pays dédupliqués et triés par étude ; textes nettoyés (espaces retirés, valeurs vides en null).
- Études sans identifiant ou sans titre écartées ; doublons sur `nct_id` supprimés.

## Schéma

| Champ | Type | Description |
|---|---|---|
| nct_id | texte | Identifiant ClinicalTrials.gov (clé primaire) |
| title | texte | Titre court |
| status | texte | Statut global de l'étude |
| study_type | texte | Type d'étude (interventionnelle, observationnelle...) |
| phases | liste de textes | Phases de l'étude |
| start_date | date | Date de début |
| completion_date | date | Date de fin |
| enrollment | entier | Nombre de participants |
| conditions | liste de textes | Conditions étudiées (texte libre) |
| sponsor | texte | Sponsor principal |
| sponsor_class | texte | Catégorie du sponsor |
| countries | liste de textes | Pays des sites d'étude |
| min_age_years | entier | Âge minimum en années |
| sex | texte | Sexe éligible (ALL, FEMALE, MALE) |
| has_results | booléen | Résultats publiés dans la base |

## Utilisation

```python
from datasets import load_dataset
ds = load_dataset("Asmae04/clinicaltrials-studies", split="train")
```

Tant que le dépôt est privé, connectez-vous d'abord avec `huggingface-cli login`.

## Limites connues

- Instantané figé à la date de collecte : les données de la source changent chaque jour, et l'année 2026 est incomplète.
- Les conditions sont du texte libre : des variantes d'un même terme sont comptées séparément, et « Healthy » désigne des volontaires sains, pas une maladie.
- Certains sponsors sont masqués (« [Redacted] ») et leur catégorie est alors vide.
- `has_results` vaut faux pour les études récentes qui n'ont pas encore pu publier de résultats : ce n'est pas une absence définitive.
- Le champ `enrollment` ne distingue pas les effectifs réels des effectifs estimés.
- Les dates partielles complétées au 1er du mois peuvent produire une fin antérieure au début.

## Reproductibilité

Le code du pipeline (ingestion, transformation, schéma SQL, tests) est dans le dépôt GitHub du projet : https://github.com/Asmaekaysouny/pipeline-donnees-clinicalTrials. Version publiée : v1.0.0.
