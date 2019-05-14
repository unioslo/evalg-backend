from evalg.database.query import get_or_create
from evalg.proc.person import search_persons


def test_search_persons(db_session, persons):
    results = search_persons(db_session, 'foo')
    assert results.count() == 1