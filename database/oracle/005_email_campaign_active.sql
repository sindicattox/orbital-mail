-- Oculta campanhas legadas e permite controlar sua visibilidade no Orbital Mail.
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*)
      INTO v_count
      FROM user_tab_columns
     WHERE table_name = 'EMAIL_CAMPAIGN'
       AND column_name = 'ACTIVE';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE email_campaign ADD (active NUMBER(1) DEFAULT 1 NOT NULL)';
    END IF;

    UPDATE email_campaign SET active = 0;
    COMMIT;
END;
/
