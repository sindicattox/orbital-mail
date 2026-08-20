from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import AuthContext, get_auth_context
from core.database import get_db
from core.settings import get_settings
from mail.queue import (
    TEST_CAMPAIGN_PATTERN,
    TEST_CAMPAIGN_PREFIX,
    clear_pending_queue,
    count_eligible,
    dispatch_preview,
    ensure_campaign,
    insert_batch,
    list_recipients,
    queue_summary,
)
from mail.schemas import (
    CampaignCreate, CampaignDetail, CampaignSummary, CampaignUpdate, CampaignDevTestSend,
    QueuePrepareBatch, QueuePrepareStart,
)
from mail.runtime_config import effective_provider, provider_status
from mail.image_storage import materialize_markdown_data_image

router = APIRouter(tags=['Orbital Mail'])
CAMPAIGN_SELECT = '''
SELECT
    id,
    NVL(NULLIF(TRIM(internal_name), ''), NVL(NULLIF(TRIM(subject), ''), 'Campanha ' || TO_CHAR(id))) AS internal_name,
    NVL(NULLIF(TRIM(subject), ''), NVL(NULLIF(TRIM(internal_name), ''), 'Sem assunto')) AS subject,
    body_html,
    body_text,
    sender_name,
    sender_email,
    reply_to,
    NVL(LOWER(status), 'draft') AS status,
    send_date,
    created_at,
    updated_at
FROM email_campaign
'''

TECHNICAL_CAMPAIGN_FIELDS = ('internal_name', 'body_text', 'sender_name', 'sender_email', 'reply_to')


def _materialize_campaign_body(body_html: str | None, tenant_code: str) -> str | None:
    """Normalize legacy inline images using the active runtime configuration."""
    return materialize_markdown_data_image(get_settings(), tenant_code, body_html)


def _campaign_write_values(payload: CampaignCreate | CampaignUpdate, auth: AuthContext, current: dict | None = None) -> dict:
    values = payload.model_dump(mode='json')
    if auth.is_dev:
        if not values.get('internal_name') or not values.get('sender_name') or not values.get('sender_email'):
            raise HTTPException(status_code=422, detail='Informe nome interno, nome e e-mail do remetente.')
        return values

    if current is not None:
        for field in TECHNICAL_CAMPAIGN_FIELDS:
            values[field] = current.get(field)
        return values

    settings = get_settings()
    sender_email = str(settings.mail_from_address or '').strip()
    if not sender_email:
        raise HTTPException(status_code=503, detail='Configuração ausente: EMAIL_FROM_ADDRESS.')
    values.update({
        'internal_name': values['subject'].strip(),
        'body_text': None,
        'sender_name': str(settings.mail_from_name or '').strip() or 'Orbital Mail',
        'sender_email': sender_email,
        'reply_to': str(settings.mail_reply_to or '').strip() or None,
    })
    return values


def _campaign_or_404(
    db: Session,
    campaign_id: int,
    tenant_code: str,
    include_test_campaigns: bool = True,
) -> dict:
    row = db.execute(
        text(CAMPAIGN_SELECT + ' WHERE id = :id AND tenant_code = :tenant_code AND active = 1'),
        {'id': campaign_id, 'tenant_code': tenant_code},
    ).mappings().one_or_none()
    if row is None or (
        not include_test_campaigns
        and str(row.get('internal_name') or '').startswith(TEST_CAMPAIGN_PREFIX)
    ):
        raise HTTPException(status_code=404, detail='Campanha não encontrada.')
    return dict(row)


@router.get('/overview')
def overview(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_module_access()
    visibility_sql = '' if auth.is_dev else " AND NVL(internal_name, '') NOT LIKE :test_campaign_pattern"
    params = {'tenant_code': auth.tenant_code}
    if not auth.is_dev:
        params['test_campaign_pattern'] = TEST_CAMPAIGN_PATTERN
    row = db.execute(text(f'''
        SELECT
            COUNT(*) AS campaigns,
            SUM(CASE WHEN LOWER(status) = 'draft' THEN 1 ELSE 0 END) AS drafts,
            SUM(CASE WHEN LOWER(status) = 'completed' THEN 1 ELSE 0 END) AS sent
        FROM email_campaign
        WHERE tenant_code = :tenant_code AND active = 1{visibility_sql}
    '''), params).mappings().one()
    return {
        'campaigns': int(row['campaigns'] or 0),
        'drafts': int(row['drafts'] or 0),
        'sent': int(row['sent'] or 0),
    }


@router.get('/dispatch-preview')
def get_dispatch_preview(
    page: int = 1,
    page_size: int = 100,
    search: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_dev()
    page = max(page, 1)
    page_size = min(max(page_size, 10), 500)
    result = dispatch_preview(db, auth.tenant_code, page, page_size, search, auth.is_dev)
    settings = get_settings()
    result['send_enabled'] = bool(settings.mail_send_enabled)
    result['provider'] = settings.mail_provider
    result['is_dev'] = auth.is_dev
    return result


@router.get('/campaigns', response_model=list[CampaignSummary])
def list_campaigns(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_module_access()
    visibility_sql = '' if auth.is_dev else " AND NVL(internal_name, '') NOT LIKE :test_campaign_pattern"
    params = {'tenant_code': auth.tenant_code}
    if not auth.is_dev:
        params['test_campaign_pattern'] = TEST_CAMPAIGN_PATTERN
    rows = db.execute(text(CAMPAIGN_SELECT + f'''
        WHERE tenant_code = :tenant_code AND active = 1{visibility_sql}
        ORDER BY NVL(updated_at, created_at) DESC, id DESC
    '''), params).mappings()
    return [dict(row) for row in rows]


@router.get('/campaigns/{campaign_id}', response_model=CampaignDetail)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_module_access()
    return _campaign_or_404(db, campaign_id, auth.tenant_code, auth.is_dev)


@router.post('/campaigns', response_model=CampaignDetail, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_module_access()
    values = _campaign_write_values(payload, auth)
    values['body_html'] = _materialize_campaign_body(values.get('body_html'), auth.tenant_code)
    db.execute(text('''
        INSERT INTO email_campaign (
            tenant_code,
            internal_name,
            subject,
            body_html,
            body_text,
            sender_name,
            sender_email,
            reply_to,
            active,
            status,
            created_at,
            updated_at
        ) VALUES (
            :tenant_code,
            :internal_name,
            :subject,
            :body_html,
            :body_text,
            :sender_name,
            :sender_email,
            :reply_to,
            1,
            :status,
            SYSDATE,
            SYSDATE
        )
    '''), {**values, 'tenant_code': auth.tenant_code})
    campaign_id = db.execute(text('''
        SELECT MAX(id)
        FROM email_campaign
        WHERE tenant_code = :tenant_code
    '''), {'tenant_code': auth.tenant_code}).scalar_one()
    db.commit()
    return _campaign_or_404(db, int(campaign_id), auth.tenant_code)


@router.put('/campaigns/{campaign_id}', response_model=CampaignDetail)
def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_module_access()
    current_campaign = _campaign_or_404(db, campaign_id, auth.tenant_code, auth.is_dev)
    current = str(current_campaign.get('status') or 'draft').lower()
    if current in {'sending', 'completed'}:
        raise HTTPException(status_code=409, detail='Não é possível alterar uma campanha em envio ou já enviada.')

    values = _campaign_write_values(payload, auth, current_campaign)
    values['body_html'] = _materialize_campaign_body(values.get('body_html'), auth.tenant_code)
    result = db.execute(text('''
        UPDATE email_campaign
        SET internal_name = :internal_name,
            subject = :subject,
            body_html = :body_html,
            body_text = :body_text,
            sender_name = :sender_name,
            sender_email = :sender_email,
            reply_to = :reply_to,
            status = :status,
            updated_at = SYSDATE
        WHERE id = :id
          AND tenant_code = :tenant_code
    '''), {**values, 'id': campaign_id, 'tenant_code': auth.tenant_code})
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=404, detail='Campanha não encontrada.')
    db.commit()
    return _campaign_or_404(db, campaign_id, auth.tenant_code)


@router.delete('/campaigns/{campaign_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_module_access()
    current_campaign = _campaign_or_404(db, campaign_id, auth.tenant_code, auth.is_dev)
    current = str(current_campaign.get('status') or 'draft').lower()
    if current not in {'draft', 'ready', 'error', 'paused'}:
        raise HTTPException(status_code=409, detail='Não é possível remover uma campanha em envio ou já enviada.')

    db.execute(text('''
        DELETE FROM email_campaign
        WHERE id = :id AND tenant_code = :tenant_code
    '''), {'id': campaign_id, 'tenant_code': auth.tenant_code})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/recipient-filters')
def recipient_filters(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_dev()
    associative = db.execute(text('''
        SELECT code, name FROM br_situacao_associativa
         WHERE active = 1 ORDER BY name
    ''')).mappings()
    functional = db.execute(text('''
        SELECT code, name FROM br_situacao_funcional
         WHERE active = 1 ORDER BY name
    ''')).mappings()
    profiles = db.execute(text('''
        SELECT code, name
          FROM etype
         WHERE tenant_code = :tenant_code
           AND NVL(active, 0) = 1
         ORDER BY NVL(is_admin, 0) DESC, name, code
    '''), {'tenant_code': auth.tenant_code}).mappings()
    return {
        'associative': [dict(row) for row in associative],
        'functional': [dict(row) for row in functional],
        'profiles': [dict(row) for row in profiles],
    }


@router.get('/campaigns/{campaign_id}/recipients')
def campaign_recipients(
    campaign_id: int,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_dev()
    ensure_campaign(db, campaign_id, auth.tenant_code, auth.is_dev)
    page = max(page, 1)
    page_size = min(max(page_size, 10), 200)
    return list_recipients(db, campaign_id, auth.tenant_code, page, page_size, search, status_filter)


@router.get('/campaigns/{campaign_id}/queue')
def get_campaign_queue(
    campaign_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_dev()
    ensure_campaign(db, campaign_id, auth.tenant_code, auth.is_dev)
    return queue_summary(db, campaign_id, auth.tenant_code)


@router.post('/campaigns/{campaign_id}/queue/prepare/start')
def start_queue_preparation(
    campaign_id: int,
    payload: QueuePrepareStart,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_dev()
    ensure_campaign(db, campaign_id, auth.tenant_code, auth.is_dev)
    current = queue_summary(db, campaign_id, auth.tenant_code)
    if current['total'] > 0:
        raise HTTPException(
            status_code=409,
            detail='A campanha já possui fila. Limpe a fila antes de preparar novamente.',
        )
    cutoff = datetime.now()
    total = count_eligible(
        db, auth.tenant_code, payload.associative_code, payload.functional_code,
        payload.profile_code, payload.test_email, cutoff,
    )
    return {
        'campaign_id': campaign_id,
        'associative_code': payload.associative_code,
        'functional_code': payload.functional_code,
        'profile_code': payload.profile_code,
        'test_email': str(payload.test_email) if payload.test_email else None,
        'cutoff': cutoff,
        'target_total': total,
        'queued_total': 0,
    }


@router.post('/campaigns/{campaign_id}/queue/prepare/batch')
def prepare_queue_batch(
    campaign_id: int,
    payload: QueuePrepareBatch,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_dev()
    ensure_campaign(db, campaign_id, auth.tenant_code, auth.is_dev)
    before = queue_summary(db, campaign_id, auth.tenant_code)['total']
    insert_batch(
        db, campaign_id, auth.tenant_code, payload.associative_code, payload.functional_code,
        payload.profile_code, str(payload.test_email) if payload.test_email else None,
        payload.cutoff, payload.batch_size,
    )
    summary = queue_summary(db, campaign_id, auth.tenant_code)
    inserted = max(summary['total'] - before, 0)
    done = summary['total'] >= payload.target_total or inserted == 0
    return {
        **summary,
        'inserted_now': inserted,
        'target_total': payload.target_total,
        'done': done,
    }


@router.delete('/campaigns/{campaign_id}/queue')
def delete_campaign_queue(
    campaign_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_dev()
    ensure_campaign(db, campaign_id, auth.tenant_code, auth.is_dev)
    removed = clear_pending_queue(db, campaign_id, auth.tenant_code)
    return {'removed': removed}


@router.post('/campaigns/{campaign_id}/dev-test-send')
def start_dev_campaign_test(
    campaign_id: int,
    payload: CampaignDevTestSend,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require_dev()
    campaign = _campaign_or_404(db, campaign_id, auth.tenant_code, auth.is_dev)
    settings = get_settings()
    if not settings.mail_send_enabled:
        raise HTTPException(status_code=409, detail='Envio bloqueado por EMAIL_SEND_ENABLED=false.')

    summary = queue_summary(db, campaign_id, auth.tenant_code)
    target = str(payload.test_email).strip().lower()
    if summary['total'] <= 0:
        raise HTTPException(status_code=409, detail='Prepare a fila de teste antes de iniciar o envio.')
    if summary['processing'] or summary['sent'] or summary['errors']:
        raise HTTPException(status_code=409, detail='O teste exige uma fila nova, somente com itens pendentes.')
    if summary['pending'] != summary['total'] or summary['distinct_emails'] != 1 or summary['single_email'] != target:
        raise HTTPException(
            status_code=409,
            detail='Trava de segurança: todos os itens da fila precisam apontar exclusivamente para o e-mail de teste informado.',
        )

    provider = effective_provider(db, auth.tenant_code, settings)
    if provider not in {'ses', 'smtp2go', 'smtp'}:
        raise HTTPException(status_code=409, detail='Provider de envio não configurado.')
    readiness = provider_status(settings, provider)
    if not readiness['configured']:
        raise HTTPException(status_code=409, detail=f'Provider {provider} não está configurado: {readiness["detail"]}.')

    current = str(campaign.get('status') or 'draft').lower()
    if current not in {'draft', 'ready', 'paused', 'error'}:
        raise HTTPException(status_code=409, detail=f'Campanha em status {current} não pode iniciar este teste.')

    db.execute(text('''
        UPDATE email_queue
           SET provider = :provider, updated_at = SYSDATE
         WHERE email_campaign_id = :campaign_id
           AND LOWER(tenant_code) = LOWER(:tenant_code)
           AND LOWER(status) = 'pending'
    '''), {'provider': provider, 'campaign_id': campaign_id, 'tenant_code': auth.tenant_code})
    db.execute(text('''
        UPDATE email_campaign
           SET status = 'sending', send_date = NULL, updated_at = SYSDATE
         WHERE id = :campaign_id
           AND LOWER(tenant_code) = LOWER(:tenant_code)
    '''), {'campaign_id': campaign_id, 'tenant_code': auth.tenant_code})
    db.commit()
    return {
        'campaign_id': campaign_id,
        'status': 'sending',
        'provider': provider,
        'test_email': target,
        'messages': summary['total'],
        'message': f'Teste real iniciado: {summary["total"]} mensagem(ns), todas direcionadas para {target}.',
    }
