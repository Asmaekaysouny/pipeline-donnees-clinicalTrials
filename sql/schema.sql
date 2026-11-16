-- Schéma ClinicalTrials.gov (PostgreSQL), dérivé de docs/contrat_donnees.md

CREATE TABLE IF NOT EXISTS sponsors (
    sponsor_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    class       TEXT
);

CREATE TABLE IF NOT EXISTS studies (
    nct_id          TEXT PRIMARY KEY CHECK (nct_id ~ '^NCT[0-9]{8}$'),
    title           TEXT NOT NULL,
    status          TEXT,
    study_type      TEXT,
    start_date      DATE,
    completion_date DATE,
    enrollment      INTEGER CHECK (enrollment >= 0),
    sponsor_id      INTEGER REFERENCES sponsors (sponsor_id),
    min_age_years   SMALLINT CHECK (min_age_years BETWEEN 0 AND 120),
    sex             TEXT CHECK (sex IN ('ALL', 'FEMALE', 'MALE')),
    has_results     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS study_phases (
    nct_id  TEXT NOT NULL REFERENCES studies (nct_id) ON DELETE CASCADE,
    phase   TEXT NOT NULL,
    PRIMARY KEY (nct_id, phase)
);

CREATE TABLE IF NOT EXISTS conditions (
    condition_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS study_conditions (
    nct_id        TEXT    NOT NULL REFERENCES studies (nct_id) ON DELETE CASCADE,
    condition_id  INTEGER NOT NULL REFERENCES conditions (condition_id),
    PRIMARY KEY (nct_id, condition_id)
);

CREATE TABLE IF NOT EXISTS countries (
    country_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS study_countries (
    nct_id      TEXT    NOT NULL REFERENCES studies (nct_id) ON DELETE CASCADE,
    country_id  INTEGER NOT NULL REFERENCES countries (country_id),
    PRIMARY KEY (nct_id, country_id)
);
