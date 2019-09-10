from evalg.database.query import get_or_create
from evalg.models.group import Group
from evalg.proc.group import is_member_of_group
from evalg.proc.group import search_groups


def test_search_group(db_session):
    group = get_or_create(db_session, Group, name='foo')
    db_session.add(group)
    db_session.flush()
    results = search_groups(session=db_session, filter_string='o')
    assert results.count() == 1


def test_is_member_of_group(
        db_session,
        make_group,
        make_group_membership,
        persons):
    """Test is_member_of_group"""
    group = make_group('test_member_of̈́')
    persons = list(persons.values())
    make_group_membership = make_group_membership(group, persons[0])
    assert is_member_of_group(db_session, group, persons[0])
    assert not is_member_of_group(db_session, group, persons[1])
