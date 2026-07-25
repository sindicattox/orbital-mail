import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps' / 'api'))

from mail.queue import _recipient_filter_sql


CASES = []
for index in range(1000):
    associative = None if index % 4 == 0 else f' assoc_{index % 11} '
    functional = None if index % 5 == 0 else f' func_{index % 13} '
    CASES.append((index, associative, functional))


@pytest.mark.parametrize('index,associative,functional', CASES)
def test_dynamic_recipient_filter_contract(index, associative, functional):
    clause, params = _recipient_filter_sql(associative, functional)

    if associative:
        assert 'br_situacao_associativa_code' in clause
        assert params['associative_code'] == associative.strip()
    else:
        assert 'associative_code' not in params

    if functional:
        assert 'br_situacao_funcional_code' in clause
        assert params['functional_code'] == functional.strip()
    else:
        assert 'functional_code' not in params

    if not associative and not functional:
        assert clause == '1 = 1'
