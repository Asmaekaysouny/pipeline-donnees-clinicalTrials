-- EXPLAIN : études d'une condition donnée avec résultats publiés
EXPLAIN (ANALYZE, BUFFERS)
SELECT s.nct_id, s.title
FROM conditions c
JOIN study_conditions sc ON sc.condition_id = c.condition_id
JOIN studies s ON s.nct_id = sc.nct_id
WHERE c.name = 'Breast Cancer' AND s.has_results;
