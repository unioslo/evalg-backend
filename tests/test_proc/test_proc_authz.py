from evalg.database.query import get_or_create
from evalg.models.authorization import (PersonPrincipal,
                                        PersonIdentifierPrincipal)
from evalg.models.person import PersonExternalId, Person
from evalg.proc.authz import (can_publish_election,
                              get_or_create_principal,
                              get_person_identifier_principals,
                              get_principals_for_person)


def test_get_or_create_principal(db_session, person_foo):
    principal = get_or_create_principal(
        session=db_session,
        principal_type='person',
        person_id=person_foo.id)
    db_session.add(principal)
    db_session.flush()
    assert isinstance(principal, PersonPrincipal)
    assert principal.person_id == person_foo.id
    same_principal = get_or_create_principal(
        session=db_session,
        principal_type='person',
        person_id=person_foo.id)
    assert principal == same_principal


def test_get_person_identifier_principals(db_session, person_foo):
    feide_id_principal = get_or_create_principal(
        session=db_session,
        principal_type='person_identifier',
        id_type='feide_id',
        id_value='foo@example.org')
    db_session.add(feide_id_principal)
    other_persons_feide_id_principal = get_or_create_principal(
        session=db_session,
        principal_type='person_identifier',
        id_type='feide_id',
        id_value='bar@example.org')
    db_session.add(other_persons_feide_id_principal)
    nin_principal = get_or_create_principal(
        session=db_session,
        principal_type='person_identifier',
        id_type='nin',
        id_value='12128812345')
    db_session.add(nin_principal)
    db_session.flush()
    principals = get_person_identifier_principals(db_session, person_foo).all()
    assert feide_id_principal in principals
    assert nin_principal in principals
    assert len(principals) == 2


def test_get_principals_for_person(db_session, person_foo):
    principal = get_or_create_principal(
        session=db_session,
        principal_type='person',
        person_id=person_foo.id)
    db_session.add(principal)
    feide_id_principal = get_or_create_principal(
        session=db_session,
        principal_type='person_identifier',
        id_type='feide_id',
        id_value='foo@example.org')
    db_session.add(feide_id_principal)
    db_session.flush()
    principals = get_principals_for_person(db_session, person_foo)
    assert len(principals) == 2


def test_can_publish_election(db_session,
                              make_person,
                              make_group,
                              make_group_membership):
    """Test can_publish_election."""
    publisher_group = make_group('publisher')
    person_a = make_person('test_can_publish_a', 'can_publish@a.no')
    person_b = make_person('test_can_publish_b', 'can_publish@b.no')
    make_group_membership(publisher_group, person_a)
    assert can_publish_election(db_session, person_a)
    assert not can_publish_election(db_session, person_b)
