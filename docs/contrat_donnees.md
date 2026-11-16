# Contrat de données

Source : ClinicalTrials.gov, API v2. Format brut : JSON Lines, une étude par ligne.
Les chemins partent de `protocolSection`, sauf `hasResults` (racine de l'étude).

| Champ | Chemin | Type |
|---|---|---|
| nct_id | identificationModule.nctId | texte, clé primaire |
| title | identificationModule.briefTitle | texte |
| status | statusModule.overallStatus | texte |
| study_type | designModule.studyType | texte |
| phases | designModule.phases | liste de textes |
| start_date | statusModule.startDateStruct.date | date |
| completion_date | statusModule.completionDateStruct.date | date |
| enrollment | designModule.enrollmentInfo.count | entier |
| conditions | conditionsModule.conditions | liste de textes |
| sponsor | sponsorCollaboratorsModule.leadSponsor.name | texte |
| sponsor_class | sponsorCollaboratorsModule.leadSponsor.class | texte |
| countries | contactsLocationsModule.locations[].country | liste de textes |
| min_age_years | eligibilityModule.minimumAge | entier (années) |
| sex | eligibilityModule.sex | texte |
| has_results | hasResults | booléen |

## Règles
- Les e-mails de contact sont exclus (conditions d'utilisation de la source).
- Dates partielles complétées au 1er du mois.
- Études sans identifiant ou sans titre écartées ; doublons sur nct_id supprimés.
