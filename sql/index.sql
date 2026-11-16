-- Index justifié : retrouver les études d'une condition
CREATE INDEX IF NOT EXISTS idx_study_conditions_condition ON study_conditions (condition_id);
ANALYZE study_conditions;
