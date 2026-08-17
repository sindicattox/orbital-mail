from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_campaigns_are_filtered_by_active_and_new_campaigns_are_active():
    router = (ROOT / "apps/api/mail/router.py").read_text()

    assert router.count("active = 1") >= 3
    assert "reply_to,\n            active,\n            status" in router
    assert ":reply_to,\n            1,\n            :status" in router


def test_active_migration_hides_existing_campaigns():
    migration = (ROOT / "database/oracle/005_email_campaign_active.sql").read_text().lower()

    assert "alter table email_campaign add (active number(1) default 1 not null)" in migration
    assert "update email_campaign set active = 0" in migration
