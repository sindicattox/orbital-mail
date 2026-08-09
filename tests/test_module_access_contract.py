import pytest
from fastapi import HTTPException

from core.auth import _context_from_payload


def test_v1_module_access_comes_from_orbital_app_permission():
    context = _context_from_payload({
        "user_id": 10,
        "tenant_code": "ANPPREV",
        "is_admin": False,
        "is_dev": False,
        "permissions": [
            {"page_alias": "orbital-mail-home", "action_code": "access_page"},
        ],
    })
    context.require_module_access()
    assert context.tenant_code == "anpprev"


def test_admin_does_not_bypass_etype_permission():
    context = _context_from_payload({
        "user_id": 11,
        "tenant_code": "asaclub",
        "is_admin": True,
        "is_dev": False,
        "permissions": [],
    })
    with pytest.raises(HTTPException) as exc_info:
        context.require_module_access()
    assert exc_info.value.status_code == 403


def test_dev_bypasses_permission_but_keeps_current_tenant():
    context = _context_from_payload({
        "user_id": 12,
        "tenant_code": "ASACLUB",
        "is_admin": False,
        "is_dev": True,
        "permissions": [],
    })
    context.require_module_access()
    assert context.tenant_code == "asaclub"


def test_other_page_permission_does_not_grant_mail():
    context = _context_from_payload({
        "user_id": 13,
        "tenant_code": "anpprev",
        "permissions": [
            {"page_alias": "orbital-reports-home", "action_code": "access_page"},
        ],
    })
    with pytest.raises(HTTPException) as exc_info:
        context.require_module_access()
    assert exc_info.value.status_code == 403
