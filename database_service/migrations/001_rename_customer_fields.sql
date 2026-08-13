BEGIN;

ALTER TABLE customers
    RENAME COLUMN phone_no TO phone_number;

ALTER TABLE customers
    RENAME COLUMN credit_default TO "default";

ALTER TABLE customers
    RENAME COLUMN housing_loan TO housing;

ALTER TABLE customers
    RENAME COLUMN personal_loan TO loan;

ALTER TABLE historical_data
    RENAME COLUMN credit_default TO "default";

ALTER TABLE historical_data
    RENAME COLUMN housing_loan TO housing;

ALTER TABLE historical_data
    RENAME COLUMN personal_loan TO loan;

COMMIT;
