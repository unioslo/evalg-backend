from evalg.database.query import get_or_create
from evalg.models.group import Group
from evalg.proc.group import search_groups


def test_search_group(db_session):
    group = get_or_create(db_session, Group, name='foo')
    db_session.add(group)
    db_session.flush()
    results = search_groups(session=db_session, filter_string='o')
    assert results.count() == 1