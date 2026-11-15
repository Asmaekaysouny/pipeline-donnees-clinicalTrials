-- Vide toutes les tables (rechargement complet depuis le Parquet)
TRUNCATE study_countries, study_conditions, study_phases, studies, countries, conditions, sponsors RESTART IDENTITY;
