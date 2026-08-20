import base64

from core.settings import Settings
from mail.image_storage import materialize_markdown_data_image


def test_legacy_markdown_data_image_is_published_as_html(tmp_path):
    settings = Settings.model_construct(
        mail_upload_dir=str(tmp_path),
        mail_public_upload_url="https://admin.sindicatto.com/orbital-mail/api/mail/uploads",
        mail_upload_max_bytes=5_242_880,
    )
    payload = b"fake png payload"
    encoded = base64.b64encode(payload).decode()

    result = materialize_markdown_data_image(
        settings,
        "ASACLUB",
        f"![](data:image/png;base64,{encoded})",
    )

    assert result.startswith('<p><img src="https://admin.sindicatto.com/orbital-mail/api/mail/uploads/asaclub/')
    assert result.endswith('.png" alt="Imagem da campanha" style="display:block;width:100%;max-width:100%;height:auto;margin:0 auto;"></p>')
    files = list((tmp_path / "asaclub").iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == payload


def test_regular_html_is_unchanged(tmp_path):
    settings = Settings.model_construct(
        mail_upload_dir=str(tmp_path),
        mail_public_upload_url="https://admin.sindicatto.com/orbital-mail/api/mail/uploads",
        mail_upload_max_bytes=5_242_880,
    )
    html = '<p><img src="https://example.com/image.png"></p>'

    assert materialize_markdown_data_image(settings, "asaclub", html) == html
    assert list(tmp_path.iterdir()) == []


def test_campaign_router_uses_runtime_settings_for_legacy_image(tmp_path, monkeypatch):
    from mail import router

    settings = Settings.model_construct(
        mail_upload_dir=str(tmp_path / "tenants/{tenant}/media/email_campaign"),
        mail_public_upload_url="https://admin.sindicatto.com/orbital-mail/api/mail/uploads",
        mail_upload_max_bytes=5_242_880,
    )
    monkeypatch.setattr(router, "get_settings", lambda: settings)
    payload = b"router regression payload"
    encoded = base64.b64encode(payload).decode()

    result = router._materialize_campaign_body(
        f"![](data:image/png;base64,{encoded})",
        "ASACLUB",
    )

    assert result.startswith(
        '<p><img src="https://admin.sindicatto.com/orbital-mail/api/mail/uploads/asaclub/'
    )
    files = list((tmp_path / "tenants/asaclub/media/email_campaign").iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == payload


def test_create_and_update_share_campaign_body_materialization_helper():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "apps/api/mail/router.py").read_text()
    call = "_materialize_campaign_body(values.get('body_html'), auth.tenant_code)"

    assert source.count(call) == 2
    assert "materialize_markdown_data_image(settings, auth.tenant_code" not in source
