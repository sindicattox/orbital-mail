from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


def ensure_campaign(db: Session, campaign_id: int, tenant_code: str) -> None:
    exists = db.execute(
        text('''
            SELECT 1
              FROM email_campaign
             WHERE id = :campaign_id
               AND LOWER(tenant_code) = LOWER(:tenant_code)
        '''),
        {'campaign_id': campaign_id, 'tenant_code': tenant_code},
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail='Campanha não encontrada.')


def queue_summary(db: Session, campaign_id: int, tenant_code: str) -> dict:
    row = db.execute(
        text('''
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN LOWER(status) = 'pending' THEN 1 ELSE 0 END) AS pending,
                   SUM(CASE WHEN LOWER(status) = 'processing' THEN 1 ELSE 0 END) AS processing,
                   SUM(CASE WHEN LOWER(status) = 'sent' THEN 1 ELSE 0 END) AS sent,
                   SUM(CASE WHEN LOWER(status) IN ('error', 'invalid_email') THEN 1 ELSE 0 END) AS errors
              FROM email_queue
             WHERE email_campaign_id = :campaign_id
               AND LOWER(tenant_code) = LOWER(:tenant_code)
        '''),
        {'campaign_id': campaign_id, 'tenant_code': tenant_code},
    ).mappings().one()
    return {key: int(row[key] or 0) for key in ('total', 'pending', 'processing', 'sent', 'errors')}


def _recipient_filter_sql(
    associative_code: str | None,
    functional_code: str | None,
    profile_code: str | None = None,
) -> tuple[str, dict]:
    clauses: list[str] = []
    params: dict[str, str] = {}
    if associative_code:
        clauses.append('LOWER(m.br_situacao_associativa_code) = LOWER(:associative_code)')
        params['associative_code'] = associative_code.strip()
    if functional_code:
        clauses.append('LOWER(m.br_situacao_funcional_code) = LOWER(:functional_code)')
        params['functional_code'] = functional_code.strip()
    if profile_code:
        clauses.append('LOWER(m.etype_code) = LOWER(:profile_code)')
        params['profile_code'] = profile_code.strip()
    return (' AND '.join(clauses) if clauses else '1 = 1'), params


def count_eligible(
    db: Session,
    tenant_code: str,
    associative_code: str | None,
    functional_code: str | None,
    profile_code: str | None,
    test_email: str | None,
    cutoff: datetime,
) -> int:
    filter_sql, filter_params = _recipient_filter_sql(associative_code, functional_code, profile_code)
    grouping = 'm.id' if test_email else 'LOWER(TRIM(e.email))'
    email_eligibility = '1 = 1' if test_email else "e.email IS NOT NULL AND REGEXP_LIKE(TRIM(e.email), '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$') AND b.id IS NULL"
    return int(db.execute(
        text(f'''
            SELECT COUNT(*)
              FROM (
                    SELECT {grouping} AS recipient_key
                      FROM member m
                      JOIN entity e
                        ON e.id = m.entity_id
                       AND LOWER(e.tenant_code) = LOWER(m.tenant_code)
                      LEFT JOIN email_blacklist b
                        ON LOWER(TRIM(b.email)) = LOWER(TRIM(e.email))
                       AND (b.tenant_code IS NULL OR LOWER(b.tenant_code) = LOWER(:tenant_code))
                     WHERE LOWER(m.tenant_code) = LOWER(:tenant_code)
                       AND {email_eligibility}
                       AND NVL(m.created_at, DATE '1900-01-01') <= :cutoff
                       AND NVL(m.updated_at, NVL(m.created_at, DATE '1900-01-01')) <= :cutoff
                       AND {filter_sql}
                     GROUP BY {grouping}
              )
        '''),
        {'tenant_code': tenant_code, 'cutoff': cutoff, **filter_params},
    ).scalar_one() or 0)


def insert_batch(
    db: Session,
    campaign_id: int,
    tenant_code: str,
    associative_code: str | None,
    functional_code: str | None,
    profile_code: str | None,
    test_email: str | None,
    cutoff: datetime,
    batch_size: int,
) -> int:
    filter_sql, filter_params = _recipient_filter_sql(associative_code, functional_code, profile_code)
    email_expression = ':test_email' if test_email else 'TRIM(e.email)'
    # Produção mantém a deduplicação original: PARTITION BY LOWER(TRIM(e.email)).
    partition_expression = 'm.id' if test_email else 'LOWER(TRIM(e.email))'
    duplicate_condition = 'q.member_id = m.id' if test_email else 'LOWER(TRIM(q.email)) = LOWER(TRIM(e.email))'
    email_eligibility = '1 = 1' if test_email else "e.email IS NOT NULL AND REGEXP_LIKE(TRIM(e.email), '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$') AND b.id IS NULL"
    result = db.execute(
        text(f'''
            INSERT INTO email_queue (
                email_campaign_id,
                member_id,
                member_insert_date,
                email,
                status,
                name,
                company,
                home_uf,
                work_uf,
                blocked,
                priority,
                created_at,
                tenant_code,
                try_count
            )
            SELECT :campaign_id,
                   candidate.member_id,
                   candidate.member_insert_date,
                   candidate.email,
                   'pending',
                   candidate.name,
                   candidate.company,
                   candidate.home_uf,
                   candidate.work_uf,
                   0,
                   10,
                   SYSDATE,
                   :tenant_code,
                   0
              FROM (
                    SELECT m.id AS member_id,
                           m.created_at AS member_insert_date,
                           {email_expression} AS email,
                           TRIM(e.name || ' ' || NVL(e.surname, '')) AS name,
                           t.name AS company,
                           e.home_uf,
                           e.work_uf,
                           ROW_NUMBER() OVER (
                               PARTITION BY {partition_expression}
                               ORDER BY m.id DESC
                           ) AS email_rank
                      FROM member m
                      JOIN entity e
                        ON e.id = m.entity_id
                       AND LOWER(e.tenant_code) = LOWER(m.tenant_code)
                      LEFT JOIN tenant t
                        ON LOWER(t.code) = LOWER(m.tenant_code)
                      LEFT JOIN email_blacklist b
                        ON LOWER(TRIM(b.email)) = LOWER(TRIM(e.email))
                       AND (b.tenant_code IS NULL OR LOWER(b.tenant_code) = LOWER(:tenant_code))
                     WHERE LOWER(m.tenant_code) = LOWER(:tenant_code)
                       AND {email_eligibility}
                       AND NVL(m.created_at, DATE '1900-01-01') <= :cutoff
                       AND NVL(m.updated_at, NVL(m.created_at, DATE '1900-01-01')) <= :cutoff
                       AND {filter_sql}
                       AND NOT EXISTS (
                           SELECT 1
                             FROM email_queue q
                            WHERE q.email_campaign_id = :campaign_id
                              AND LOWER(q.tenant_code) = LOWER(:tenant_code)
                              AND {duplicate_condition}
                       )
                     ORDER BY m.id
              ) candidate
             WHERE candidate.email_rank = 1
               AND ROWNUM <= :batch_size
        '''),
        {
            'campaign_id': campaign_id,
            'tenant_code': tenant_code,
            'test_email': test_email,
            'cutoff': cutoff,
            'batch_size': batch_size,
            **filter_params,
        },
    )
    db.commit()
    return max(int(result.rowcount or 0), 0)


def list_recipients(
    db: Session,
    campaign_id: int,
    tenant_code: str,
    page: int,
    page_size: int,
    search: str | None,
    status: str | None,
) -> dict:
    filters = [
        'q.email_campaign_id = :campaign_id',
        'LOWER(q.tenant_code) = LOWER(:tenant_code)',
    ]
    params: dict[str, object] = {'campaign_id': campaign_id, 'tenant_code': tenant_code}
    if search:
        filters.append("(LOWER(q.name) LIKE :search OR LOWER(q.email) LIKE :search)")
        params['search'] = f"%{search.strip().lower()}%"
    if status:
        filters.append('LOWER(q.status) = LOWER(:status)')
        params['status'] = status.strip()
    where_sql = ' AND '.join(filters)
    total = int(db.execute(text(f'SELECT COUNT(*) FROM email_queue q WHERE {where_sql}'), params).scalar_one() or 0)
    params.update({'offset_rows': (page - 1) * page_size, 'page_size': page_size})
    rows = db.execute(text(f'''
        SELECT q.id,
               q.member_id,
               q.member_insert_date,
               q.email,
               q.status,
               q.last_try,
               q.opened_at,
               q.name,
               q.company,
               q.home_uf,
               q.work_uf,
               q.blocked,
               q.priority,
               q.error,
               q.created_at,
               q.provider_message_id,
               q.provider,
               q.provider_status,
               q.provider_code,
               q.provider_last_event_at,
               q.delivered_at,
               q.last_error_class,
               q.retryable,
               q.next_try_at,
               q.try_count,
               m.br_situacao_associativa_code,
               sa.name AS br_situacao_associativa_name,
               m.br_situacao_funcional_code,
               sf.name AS br_situacao_funcional_name
          FROM email_queue q
          LEFT JOIN member m
            ON m.id = q.member_id
           AND LOWER(m.tenant_code) = LOWER(q.tenant_code)
          LEFT JOIN br_situacao_associativa sa
            ON sa.code = m.br_situacao_associativa_code
          LEFT JOIN br_situacao_funcional sf
            ON sf.code = m.br_situacao_funcional_code
         WHERE {where_sql}
         ORDER BY q.id
         OFFSET :offset_rows ROWS FETCH NEXT :page_size ROWS ONLY
    '''), params).mappings()
    return {
        'items': [dict(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': total,
        'pages': max((total + page_size - 1) // page_size, 1),
    }


def clear_pending_queue(db: Session, campaign_id: int, tenant_code: str) -> int:
    busy = int(db.execute(
        text('''
            SELECT COUNT(*)
              FROM email_queue
             WHERE email_campaign_id = :campaign_id
               AND LOWER(tenant_code) = LOWER(:tenant_code)
               AND LOWER(status) IN ('processing', 'sent')
        '''),
        {'campaign_id': campaign_id, 'tenant_code': tenant_code},
    ).scalar_one() or 0)
    if busy:
        raise HTTPException(status_code=409, detail='A fila já possui mensagens processadas ou enviadas.')

    result = db.execute(
        text('''
            DELETE FROM email_queue
             WHERE email_campaign_id = :campaign_id
               AND LOWER(tenant_code) = LOWER(:tenant_code)
        '''),
        {'campaign_id': campaign_id, 'tenant_code': tenant_code},
    )
    db.commit()
    return max(int(result.rowcount or 0), 0)
