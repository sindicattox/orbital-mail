from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

from core.settings import get_settings
from mail.unsubscribe import (
    append_unsubscribe_footer,
    create_unsubscribe_token,
    one_click_unsubscribe_url,
    read_unsubscribe_token,
    unsubscribe_headers,
)


def _settings(monkeypatch):
    monkeypatch.setenv("MAIL_UNSUBSCRIBE_SECRET", "test-secret-with-enough-entropy")
    monkeypatch.setenv("MAIL_PUBLIC_URL", "https://orbital-mail.asaclub.org.br")
    get_settings.cache_clear()


def test_token_preserves_tenant_scope(monkeypatch):
    _settings(monkeypatch)
    token = create_unsubscribe_token("Pessoa@Email.com", "ASACLUB", 77)
    payload = read_unsubscribe_token(token)
    assert payload == {
        "email": "pessoa@email.com",
        "tenant_code": "asaclub",
        "campaign_id": 77,
    }


def test_token_rejects_tampering(monkeypatch):
    _settings(monkeypatch)
    token = create_unsubscribe_token("pessoa@email.com", "asaclub", 77)
    encoded, signature = token.split(".", 1)
    with pytest.raises(HTTPException) as exc:
        read_unsubscribe_token(f"{encoded}x.{signature}")
    assert exc.value.status_code == 400


def test_footer_and_one_click_headers(monkeypatch):
    _settings(monkeypatch)
    url = "https://orbital-mail.asaclub.org.br/unsubscribe?token=abc"
    html, text = append_unsubscribe_footer("<p>Mensagem</p>", "Mensagem", url)
    one_click_url = one_click_unsubscribe_url("pessoa@email.com", "asaclub", 77)
    headers = unsubscribe_headers(one_click_url)
    assert "Descadastrar" in html
    assert url in html
    assert url in text
    assert "/api/mail/public/unsubscribe?token=" in one_click_url
    assert headers["List-Unsubscribe"] == f"<{one_click_url}>"
    assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


def test_merge_is_strictly_per_tenant():
    source = (API / "mail" / "unsubscribe.py").read_text()
    assert "LOWER(TRIM(b.tenant_code)) = src.tenant_code" in source
    assert "tenant_code IS NULL" not in source
    assert "b.source = 'unsubscribe'" in source
    assert "b.permanent = 1" in source


def test_public_page_does_not_use_authenticated_layout():
    page = (ROOT / "apps" / "web" / "src" / "pages" / "unsubscribe.astro").read_text()
    assert "AppLayout" not in page
    assert "${apiUrl}/public/unsubscribe" in page
    assert "Confirmar descadastro" in page
