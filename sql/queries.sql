-- 1. Nombre d'études par statut
SELECT status, COUNT(*) AS nombre_etudes
FROM studies
GROUP BY status
ORDER BY nombre_etudes DESC;

-- 2. Les 10 conditions médicales les plus fréquentes
SELECT c.name, COUNT(*) AS nombre_etudes
FROM conditions c
JOIN study_conditions sc ON c.condition_id = sc.condition_id
GROUP BY c.name
ORDER BY nombre_etudes DESC
LIMIT 10;

-- 3. Les 10 pays qui participent au plus grand nombre d'études
SELECT co.name, COUNT(*) AS nombre_etudes
FROM countries co
JOIN study_countries sc ON co.country_id = sc.country_id
GROUP BY co.name
ORDER BY nombre_etudes DESC
LIMIT 10;

-- 4. Les 10 sponsors ayant le plus d'études
SELECT sp.name, COUNT(*) AS nombre_etudes
FROM sponsors sp
JOIN studies s ON sp.sponsor_id = s.sponsor_id
GROUP BY sp.name
ORDER BY nombre_etudes DESC
LIMIT 10;

-- 5. Répartition des études par phase
SELECT phase, COUNT(*) AS nombre_etudes
FROM study_phases
GROUP BY phase
ORDER BY nombre_etudes DESC;
