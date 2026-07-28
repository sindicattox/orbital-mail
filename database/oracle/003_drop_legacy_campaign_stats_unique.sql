-- Remove a unicidade legada por assunto e data de envio.
-- Campanhas diferentes podem ter o mesmo assunto e rascunhos não possuem SEND_DATE.

BEGIN
    EXECUTE IMMEDIATE '
        ALTER TABLE EMAIL_CAMPAIGN
        DROP CONSTRAINT UK_EMAIL_CAMPAIGN_STATS
    ';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -2443 THEN
            RAISE;
        END IF;
END;
/

COMMIT;
