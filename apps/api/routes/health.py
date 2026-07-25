from fastapi import APIRouter
from sqlalchemy import text
from core.database import get_engine
from core.settings import get_settings
router=APIRouter(tags=['Health'])
@router.get('/health')
def health():
    settings=get_settings(); database='not-configured'
    if settings.oracle_user and settings.oracle_password:
        try:
            with get_engine().connect() as c: c.execute(text('SELECT 1 FROM DUAL')); database='ok'
        except Exception: database='error'
    return {'status':'ok','app':settings.app_name,'environment':settings.app_env,'database':database,'mail_provider':settings.mail_provider,'send_enabled':settings.mail_send_enabled}
