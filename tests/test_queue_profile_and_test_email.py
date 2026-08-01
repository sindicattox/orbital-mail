from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8").lower()


def test_profile_filter_is_available_in_api_and_ui():
    queue = read("apps/api/mail/queue.py")
    router = read("apps/api/mail/router.py")
    component = read("apps/web/public/components/mail.js")
    assert "m.etype_code" in queue
    assert "from etype" in router
    assert "data-queue-profile" in component
    assert "profile_code" in component


def test_test_email_preserves_one_queue_row_per_member():
    queue = read("apps/api/mail/queue.py")
    component = read("apps/web/public/components/mail.js")
    assert "grouping = 'm.id' if test_email" in queue
    assert "partition_expression = 'm.id' if test_email" in queue
    assert "duplicate_condition = 'q.member_id = m.id' if test_email" in queue
    assert "data-queue-test-email" in component
    assert "test_email" in component


def test_test_email_is_validated():
    from mail.schemas import QueuePrepareStart
    try:
        QueuePrepareStart(test_email="invalido")
    except ValidationError:
        return
    raise AssertionError("E-mail de teste inválido foi aceito")


def test_queue_only_selects_active_non_removed_members_and_entities():
    queue = read("apps/api/mail/queue.py")
    assert queue.count("and nvl(m.active, 0) = 1") == 2
    assert queue.count("and nvl(e.active, 0) = 1") == 2
    assert queue.count("and m.removed_at is null") == 2
