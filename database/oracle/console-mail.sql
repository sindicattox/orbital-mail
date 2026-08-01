SELECT
    m.id AS member_id,
    TRIM(e.name || ' ' || NVL(e.surname, '')) AS nome,
    LOWER(TRIM(e.email)) AS email,
    m.etype_code,
    m.active,
    m.br_situacao_associativa_code,
    m.br_situacao_funcional_code
FROM member m
JOIN entity e
     ON e.id = m.entity_id
         AND LOWER(e.tenant_code) = LOWER(m.tenant_code)
LEFT JOIN email_blacklist b
          ON LOWER(TRIM(b.email)) = LOWER(TRIM(e.email))
              AND (
                 b.tenant_code IS NULL
                     OR LOWER(TRIM(b.tenant_code)) = 'asaclub'
                 )
WHERE LOWER(TRIM(m.tenant_code)) = 'asaclub'
    AND LOWER(TRIM(m.etype_code)) = 'associate'
    AND NVL(m.active, 0) = 1
    AND e.email IS NOT NULL
    AND REGEXP_LIKE(
        TRIM(e.email),
        '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'
        )
    AND b.id IS NULL
ORDER BY LOWER(TRIM(e.email));