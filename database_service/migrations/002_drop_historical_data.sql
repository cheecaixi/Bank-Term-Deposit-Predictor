-- Removes the historical_data table from the database if it already exists

BEGIN;

DROP TABLE IF EXISTS historical_data;

COMMIT;
