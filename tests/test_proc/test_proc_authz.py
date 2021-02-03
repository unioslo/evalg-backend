from evalg.models.authorization import PersonPrincipal
from evalg.proc.authz import (get_or_create_principal,
                              get_person_identifier_principals,
                              get_principals_for_person)


def test_get_or_create_principal(db_session, person_generator):
    person = person_generator()
    principal = get_or_create_principal(
        session=db_session,
        principal_type='person',
        person_id=person.id)
    db_session.add(principal)
    db_session.flush()
    assert isinstance(principal, PersonPrincipal)
    assert principal.person_id == person.id
    same_principal = get_or_create_principal(
        session=db_session,
        principal_type='person',
        person_id=person.id)
    assert principal == same_principal


def test_get_person_identifier_principals(db_session, person_generator):
    person = person_generator()
    feide_id = [x.id_value for x in person.identifiers
                if x.id_type == 'feide_id'][0]
    nin = [x.id_value for x in person.identifiers if x.id_type == 'nin'][0]
    feide_id_principal = get_or_create_principal(
        session=db_session,
        principal_type='person_identifier',
        id_type='feide_id',
        id_value=feide_id)
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
        id_value=nin)
    db_session.add(nin_principal)
    db_session.flush()
    principals = get_person_identifier_principals(db_session, person).all()
    assert feide_id_principal in principals
    assert nin_principal in principals
    assert len(principals) == 2


def test_get_principals_for_person(db_session, person_generator):
    person = person_generator()
    feide_id = [x.id_value for x in person.identifiers
                if x.id_type == 'feide_id'][0]
    principal = get_or_create_principal(
        session=db_session,
        principal_type='person',
        person_id=person.id)
    db_session.add(principal)
    feide_id_principal = get_or_create_principal(
        session=db_session,
        principal_type='person_identifier',
        id_type='feide_id',
        id_value=feide_id)
    db_session.add(feide_id_principal)
    db_session.flush()
    principals = get_principals_for_person(db_session, person)
    assert len(principals) == 2
