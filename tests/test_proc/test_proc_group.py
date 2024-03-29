from evalg.database.query import get_or_create
from evalg.models.group import Group
from evalg.models.group import GroupMembership

from evalg.proc.group import (add_person_to_group,
                              get_group_by_id,
                              get_group_by_name,
                              get_user_groups,
                              is_member_of_group,
                              remove_person_from_group,
                              search_groups)


def test_search_group(db_session):
    group = get_or_create(db_session, Group, name='foo1234-123')
    db_session.add(group)
    db_session.flush()
    results = search_groups(session=db_session, filter_string='foo1234')
    assert results.count() == 1


def test_get_group_by_name(db_session, group_generator):
    """Test get_group_by_name."""
    group_name = 'test_get_group_by_name'
    group_error = 'test_get_group_by_name_error'
    group_foo = group_generator(db_session, group_name)
    assert get_group_by_name(db_session, group_name).id == group_foo.id
    assert get_group_by_name(db_session, group_error) is None


def test_get_group_by_id(db_session, group_generator):
    """Test get_group_by_id."""
    group = group_generator(db_session, 'test_get_group_by_id')
    res = get_group_by_id(db_session, group.id)
    assert res
    assert res.id == group.id
    assert res.name == group.name


def test_is_member_of_group(
        db_session,
        group_generator,
        make_group_membership,
        persons):
    """Test is_member_of_group."""
    group = group_generator(db_session, 'test_member_of̈́')
    persons = list(persons.values())
    group_membership = make_group_membership(db_session, group, persons[0])
    assert group_membership
    assert is_member_of_group(db_session, group, persons[0])
    assert not is_member_of_group(db_session, group, persons[1])


def test_add_person_to_group(db_session, group_generator, person_generator):
    """Test add_person_to_group"""
    group = group_generator(db_session, 'test_add_person_to_group')
    person = person_generator('test_add_person_to_group', 'add@group.no')
    membership = add_person_to_group(db_session, group, person)
    assert membership
    membership_db = GroupMembership.query.get(membership.id)
    assert membership_db
    assert membership_db.person_id == membership.person_id
    assert membership_db.group_id == membership.group_id


def test_remove_person_from_group(
        db_session,
        group_generator,
        make_group_membership,
        person_generator):
    """Test remove_person_from_group"""
    person = person_generator('remove_person_from_group', 'remove@group.no')
    group = group_generator(db_session, 'remove_person_from_group_test')
    membership = make_group_membership(db_session, group, person)
    assert membership
    remove_person_from_group(db_session, group, person)
    membership_db = GroupMembership.query.get(membership.id)
    assert not membership_db


def test_get_user_groups(
        db_session,
        group_generator,
        make_group_membership,
        person_generator):
    """Test get_user_groups."""
    person_a = person_generator('test_get_user_groups_a',
                                'test_get_user_groups@foo.no')
    person_b = person_generator('test_get_user_groups_b',
                                'test_get_user_groups@bar.no')
    groups = [group_generator(db_session, 'test_get_user_groups_a'),
              group_generator(db_session, 'test_get_user_groups_b')]
    memberships = [make_group_membership(db_session, x, person_a) for x in
                   groups]

    res_a = get_user_groups(db_session, person_a)
    assert res_a
    assert len(res_a) == len(groups)

    res_a_ids = [x.id for x in res_a]
    membership_group_ids = [x.group_id for x in memberships]
    assert all(x in res_a_ids for x in membership_group_ids)

    res_b = get_user_groups(db_session, person_b)
    assert not res_b
    assert len(res_b) == 0
