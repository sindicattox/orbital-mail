DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM user_tables WHERE table_name = 'EMAIL_DELIVERY_CONFIG';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE email_delivery_config (
                tenant_code VARCHAR2(64 CHAR) PRIMARY KEY,
                provider VARCHAR2(20 CHAR) NOT NULL,
                updated_by NUMBER,
                updated_at DATE DEFAULT SYSDATE NOT NULL,
                CONSTRAINT ck_email_delivery_config_provider CHECK (provider IN ('ses','smtp2go','smtp'))
            )
        ]';
    END IF;
END;
/
