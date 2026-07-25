
-- ============================================================================
-- ORBITAL MAIL - MIGRACAO DO MODELO DE ENVIO E EVENTOS
-- Schema: WKSP_SINDICATTO
--
-- Objetivos:
-- 1) Remover a duplicacao EMAIL_CAMPAIGN_RECIPIENT x EMAIL_QUEUE.
-- 2) Manter EMAIL_QUEUE como estado atual de cada envio.
-- 3) Manter EMAIL_SEND_LOG como historico imutavel de tentativas e eventos.
-- 4) Evoluir EMAIL_BLACKLIST para bloqueio global ou por tenant.
-- 5) Preparar o banco para SMTP2GO, Amazon SES e SMTP tradicional.
--
-- IMPORTANTE:
-- - Execute primeiro em homologacao.
-- - O script cria um backup de EMAIL_CAMPAIGN_RECIPIENT antes de remove-la.
-- - Nao cria tabela nova de destinatarios.
-- - Nao altera EMAIL_QUEUE para impedir repeticoes, pois o teste controlado
--   pode criar mais de um envio para o mesmo e-mail na mesma campanha.
-- ============================================================================

SET DEFINE OFF;
SET SERVEROUTPUT ON;

-- ============================================================================
-- 0. BACKUP E REMOCAO DA TABELA DUPLICADA
-- ============================================================================

DECLARE
    v_exists NUMBER;
BEGIN
    SELECT COUNT(*)
      INTO v_exists
      FROM user_tables
     WHERE table_name = 'EMAIL_CAMPAIGN_RECIPIENT';

    IF v_exists = 1 THEN
        BEGIN
            EXECUTE IMMEDIATE '
                CREATE TABLE EMAIL_CAMPAIGN_RECIPIENT_BKP AS
                SELECT * FROM EMAIL_CAMPAIGN_RECIPIENT
            ';
            DBMS_OUTPUT.PUT_LINE(
                'Backup EMAIL_CAMPAIGN_RECIPIENT_BKP criado.'
            );
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE = -955 THEN
                    DBMS_OUTPUT.PUT_LINE(
                        'Backup EMAIL_CAMPAIGN_RECIPIENT_BKP ja existe; mantido.'
                    );
                ELSE
                    RAISE;
                END IF;
        END;

        EXECUTE IMMEDIATE '
            DROP TABLE EMAIL_CAMPAIGN_RECIPIENT CASCADE CONSTRAINTS PURGE
        ';

        DBMS_OUTPUT.PUT_LINE(
            'Tabela EMAIL_CAMPAIGN_RECIPIENT removida.'
        );
    ELSE
        DBMS_OUTPUT.PUT_LINE(
            'Tabela EMAIL_CAMPAIGN_RECIPIENT nao existe; nada a remover.'
        );
    END IF;
END;
/

-- ============================================================================
-- 1. EMAIL_CAMPAIGN
--    Cabecalho da campanha e estado geral.
-- ============================================================================

-- Remove a constraint antiga de status, se existir com outro nome conhecido.
-- O bloco ignora ORA-02443 quando a constraint nao existe.
BEGIN
    EXECUTE IMMEDIATE '
        ALTER TABLE EMAIL_CAMPAIGN
        DROP CONSTRAINT EMAIL_CAMPAIGN_STATUS_CK
    ';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -2443 THEN
            RAISE;
        END IF;
END;
/

-- Normaliza estados antigos mais comuns antes de criar a constraint.
UPDATE EMAIL_CAMPAIGN
   SET STATUS =
       CASE LOWER(TRIM(STATUS))
           WHEN 'pendente'  THEN 'draft'
           WHEN 'rascunho'  THEN 'draft'
           WHEN 'draft'     THEN 'draft'
           WHEN 'ready'     THEN 'ready'
           WHEN 'sending'   THEN 'sending'
           WHEN 'paused'    THEN 'paused'
           WHEN 'sent'      THEN 'completed'
           WHEN 'completed' THEN 'completed'
           WHEN 'cancelled' THEN 'cancelled'
           WHEN 'canceled'  THEN 'cancelled'
           WHEN 'error'     THEN 'error'
           ELSE 'draft'
       END;

ALTER TABLE EMAIL_CAMPAIGN
    MODIFY STATUS DEFAULT 'draft' NOT NULL;

ALTER TABLE EMAIL_CAMPAIGN
    ADD CONSTRAINT EMAIL_CAMPAIGN_STATUS_CK
        CHECK (
            STATUS IN (
                'draft',
                'ready',
                'sending',
                'paused',
                'completed',
                'cancelled',
                'error'
            )
        );

-- SEND_DATE deve ser preenchido quando o envio realmente iniciar.
-- Nao tornamos NOT NULL porque campanhas em rascunho ainda nao foram enviadas.

-- ============================================================================
-- 2. EMAIL_QUEUE
--    Estado atual de cada envio/destinatario.
-- ============================================================================

ALTER TABLE EMAIL_QUEUE ADD (
    PROVIDER                 VARCHAR2(30),
    PROVIDER_STATUS          VARCHAR2(50),
    PROVIDER_CODE            VARCHAR2(100),
    PROVIDER_LAST_EVENT_AT   DATE,
    DELIVERED_AT             DATE,
    LAST_ERROR_CLASS         VARCHAR2(30),
    RETRYABLE                NUMBER(1) DEFAULT 0 NOT NULL,
    NEXT_TRY_AT              DATE,
    UPDATED_AT               DATE
);

ALTER TABLE EMAIL_QUEUE
    ADD CONSTRAINT EMAIL_QUEUE_RETRYABLE_CK
        CHECK (RETRYABLE IN (0, 1));

ALTER TABLE EMAIL_QUEUE
    ADD CONSTRAINT EMAIL_QUEUE_ERROR_CLASS_CK
        CHECK (
            LAST_ERROR_CLASS IS NULL
            OR LAST_ERROR_CLASS IN (
                'recipient',
                'temporary',
                'configuration',
                'provider',
                'policy',
                'unknown'
            )
        );

CREATE INDEX IX_EMAIL_QUEUE_RETRY
    ON EMAIL_QUEUE (
        STATUS,
        RETRYABLE,
        NEXT_TRY_AT,
        PRIORITY,
        CREATED_AT
    );

CREATE INDEX IX_EMAIL_QUEUE_PROVIDER_MESSAGE
    ON EMAIL_QUEUE (
        PROVIDER,
        PROVIDER_MESSAGE_ID
    );

CREATE INDEX IX_EMAIL_QUEUE_PROVIDER_STATUS
    ON EMAIL_QUEUE (
        PROVIDER_STATUS,
        PROVIDER_LAST_EVENT_AT
    );

-- Nao criamos UNIQUE (EMAIL_CAMPAIGN_ID, EMAIL), porque o teste controlado
-- pode intencionalmente gerar mais de uma mensagem para o mesmo destinatario.
-- A deduplicacao de campanhas reais deve continuar no INSERT ... NOT EXISTS.

-- ============================================================================
-- 3. EMAIL_SEND_LOG
--    Historico imutavel de tentativas e eventos recebidos dos provedores.
-- ============================================================================

ALTER TABLE EMAIL_SEND_LOG ADD (
    EVENT_TYPE          VARCHAR2(50),
    PROVIDER            VARCHAR2(30),
    PROVIDER_CODE       VARCHAR2(100),
    ERROR_CLASS         VARCHAR2(30),
    RETRYABLE           NUMBER(1) DEFAULT 0 NOT NULL,
    RAW_RESPONSE        CLOB,
    PROVIDER_EVENT_ID   VARCHAR2(255),
    EVENT_AT            DATE DEFAULT SYSDATE NOT NULL
);

ALTER TABLE EMAIL_SEND_LOG
    ADD CONSTRAINT EMAIL_SEND_LOG_RETRYABLE_CK
        CHECK (RETRYABLE IN (0, 1));

ALTER TABLE EMAIL_SEND_LOG
    ADD CONSTRAINT EMAIL_SEND_LOG_ERROR_CLASS_CK
        CHECK (
            ERROR_CLASS IS NULL
            OR ERROR_CLASS IN (
                'recipient',
                'temporary',
                'configuration',
                'provider',
                'policy',
                'unknown'
            )
        );

-- STATUS passa a representar o resultado geral.
ALTER TABLE EMAIL_SEND_LOG
    DROP CONSTRAINT CK_EMAIL_SEND_LOG_STATUS;

UPDATE EMAIL_SEND_LOG
   SET STATUS =
       CASE LOWER(TRIM(STATUS))
           WHEN 'attempt'       THEN 'attempt'
           WHEN 'sent'          THEN 'success'
           WHEN 'success'       THEN 'success'
           WHEN 'error'         THEN 'error'
           WHEN 'invalid_email' THEN 'error'
           ELSE 'error'
       END;

ALTER TABLE EMAIL_SEND_LOG
    ADD CONSTRAINT CK_EMAIL_SEND_LOG_STATUS
        CHECK (
            STATUS IN (
                'attempt',
                'success',
                'error',
                'event'
            )
        );

CREATE INDEX IX_EMAIL_SEND_LOG_EVENT
    ON EMAIL_SEND_LOG (
        EVENT_TYPE,
        EVENT_AT
    );

CREATE INDEX IX_EMAIL_SEND_LOG_PROVIDER_MESSAGE
    ON EMAIL_SEND_LOG (
        PROVIDER,
        PROVIDER_MESSAGE_ID
    );

-- Evita processar o mesmo webhook duas vezes quando o provedor informar
-- um identificador unico de evento.
CREATE UNIQUE INDEX UK_EMAIL_SEND_LOG_PROVIDER_EVENT
    ON EMAIL_SEND_LOG (
        PROVIDER,
        PROVIDER_EVENT_ID
    );

-- ============================================================================
-- 4. EMAIL_BLACKLIST
--    Supressao local global ou por tenant.
-- ============================================================================

ALTER TABLE EMAIL_BLACKLIST ADD (
    TENANT_CODE        VARCHAR2(50),
    SOURCE             VARCHAR2(30),
    PROVIDER           VARCHAR2(30),
    PROVIDER_EVENT_ID  VARCHAR2(255),
    PERMANENT          NUMBER(1) DEFAULT 1 NOT NULL,
    UPDATED_AT         DATE
);

ALTER TABLE EMAIL_BLACKLIST
    ADD CONSTRAINT EMAIL_BLACKLIST_PERMANENT_CK
        CHECK (PERMANENT IN (0, 1));

-- Remove a unicidade antiga apenas por e-mail.
BEGIN
    EXECUTE IMMEDIATE '
        ALTER TABLE EMAIL_BLACKLIST
        DROP CONSTRAINT UQ_EMAIL_BLACKLIST_EMAIL
    ';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -2443 THEN
            RAISE;
        END IF;
END;
/

-- Garante uma linha por escopo:
-- TENANT_CODE NULL = bloqueio global.
-- TENANT_CODE preenchido = bloqueio especifico daquele tenant.
CREATE UNIQUE INDEX UK_EMAIL_BLACKLIST_SCOPE
    ON EMAIL_BLACKLIST (
        LOWER(EMAIL),
        NVL(LOWER(TENANT_CODE), '*')
    );

CREATE INDEX IX_EMAIL_BLACKLIST_TENANT
    ON EMAIL_BLACKLIST (
        TENANT_CODE,
        EMAIL
    );

CREATE UNIQUE INDEX UK_EMAIL_BLACKLIST_PROVIDER_EVENT
    ON EMAIL_BLACKLIST (
        PROVIDER,
        PROVIDER_EVENT_ID
    );

-- ============================================================================
-- 5. CONSULTAS DE REFERENCIA PARA O WORKER
-- ============================================================================

-- Verificacao antes de enviar:
--
-- SELECT 1
--   FROM EMAIL_BLACKLIST
--  WHERE LOWER(EMAIL) = LOWER(:email)
--    AND (
--          TENANT_CODE IS NULL
--          OR LOWER(TENANT_CODE) = LOWER(:tenant_code)
--        )
--  FETCH FIRST 1 ROW ONLY;
--
-- Erros definitivos do destinatario:
--   STATUS           = 'error' ou 'invalid_email'
--   BLOCKED          = 1
--   RETRYABLE        = 0
--   LAST_ERROR_CLASS = 'recipient'
--
-- Erros temporarios:
--   STATUS           = 'pending'
--   BLOCKED          = 0
--   RETRYABLE        = 1
--   NEXT_TRY_AT      = data/hora futura
--   LAST_ERROR_CLASS = 'temporary'
--
-- Erros de configuracao:
--   nao bloquear o destinatario;
--   pausar EMAIL_CAMPAIGN.STATUS = 'paused' ou 'error';
--   registrar ERROR_CLASS = 'configuration'.
--
-- Eventos posteriores:
--   delivered:
--      EMAIL_QUEUE.STATUS = 'sent'
--      PROVIDER_STATUS = 'delivered'
--      DELIVERED_AT = SYSDATE
--
--   hard_bounce / complaint / unsubscribe:
--      EMAIL_QUEUE.STATUS = 'error'
--      BLOCKED = 1
--      RETRYABLE = 0
--      inserir EMAIL_BLACKLIST
--
--   soft_bounce:
--      EMAIL_QUEUE.STATUS = 'error' ou 'pending', conforme politica
--      BLOCKED = 0
--      RETRYABLE = 1 somente se houver nova tentativa controlada
--
-- ============================================================================
-- 6. VALIDACAO FINAL
-- ============================================================================

SELECT TABLE_NAME
  FROM USER_TABLES
 WHERE TABLE_NAME IN (
     'EMAIL_CAMPAIGN',
     'EMAIL_QUEUE',
     'EMAIL_SEND_LOG',
     'EMAIL_BLACKLIST',
     'EMAIL_CAMPAIGN_RECIPIENT',
     'EMAIL_CAMPAIGN_RECIPIENT_BKP'
 )
 ORDER BY TABLE_NAME;

SELECT CONSTRAINT_NAME, TABLE_NAME, CONSTRAINT_TYPE, STATUS
  FROM USER_CONSTRAINTS
 WHERE TABLE_NAME IN (
     'EMAIL_CAMPAIGN',
     'EMAIL_QUEUE',
     'EMAIL_SEND_LOG',
     'EMAIL_BLACKLIST'
 )
 ORDER BY TABLE_NAME, CONSTRAINT_NAME;

COMMIT;
