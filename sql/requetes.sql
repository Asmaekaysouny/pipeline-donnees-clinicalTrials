-- Q1 : Top 10 des sponsors par nombre d'études (jointure + GROUP BY)
SELECT sp.name, sp.class, COUNT(*) AS nb_etudes
FROM studies s
JOIN sponsors sp ON sp.sponsor_id = s.sponsor_id
GROUP BY sp.sponsor_id, sp.name, sp.class
ORDER BY nb_etudes DESC
LIMIT 10;

-- Q2 : Top 10 des conditions et inscrits moyens (3 tables jointes + GROUP BY)
SELECT c.name, COUNT(*) AS nb_etudes, ROUND(AVG(s.enrollment)) AS inscrits_moyens
FROM conditions c
JOIN study_conditions sc ON sc.condition_id = c.condition_id
JOIN studies s ON s.nct_id = sc.nct_id
GROUP BY c.condition_id, c.name
ORDER BY nb_etudes DESC
LIMIT 10;

-- Q3 : Études par année de début et part avec résultats publiés (CTE)
WITH par_annee AS (
    SELECT EXTRACT(YEAR FROM start_date)::int AS annee,
           COUNT(*) AS nb,
           COUNT(*) FILTER (WHERE has_results) AS avec_resultats
    FROM studies
    WHERE start_date >= '2000-01-01' AND start_date < '2027-01-01'
    GROUP BY 1
)
SELECT annee, nb, avec_resultats, ROUND(100.0 * avec_resultats / nb, 1) AS pct_resultats
FROM par_annee
ORDER BY annee;

-- Q4 : Top 3 des sponsors dans chaque catégorie de sponsor (window function RANK)
WITH nb AS (
    SELECT sp.class, sp.name, COUNT(*) AS nb_etudes
    FROM studies s
    JOIN sponsors sp ON sp.sponsor_id = s.sponsor_id
    GROUP BY sp.class, sp.name
),
classes AS (
    SELECT class, name, nb_etudes,
           RANK() OVER (PARTITION BY class ORDER BY nb_etudes DESC) AS rang
    FROM nb
)
SELECT class, name, nb_etudes, rang
FROM classes
WHERE rang <= 3
ORDER BY class, rang;

-- Q5 : Variation annuelle (LAG) et moyenne glissante sur 3 ans
WITH par_annee AS (
    SELECT EXTRACT(YEAR FROM start_date)::int AS annee, COUNT(*) AS nb
    FROM studies
    WHERE start_date >= '2000-01-01' AND start_date < '2027-01-01'
    GROUP BY 1
)
SELECT annee, nb,
       nb - LAG(nb) OVER (ORDER BY annee) AS variation,
       ROUND(AVG(nb) OVER (ORDER BY annee ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)) AS moyenne_glissante_3ans
FROM par_annee
ORDER BY annee;
