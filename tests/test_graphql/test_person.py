"""Tests the person related queries."""

import pytest
import evalg.database.query
from evalg.models.person import Person, PersonExternalId


@pytest.fixture
def person_foo(db_session):
    """One person fixture."""
    data = {
        'email': 'foo@bar.org',
        'display_name': 'Foo Bar',
    }

    identifiers = [
        {
            "id_type": "feide_id",
            "id_value": "foo@bar.org",
        },
        {
            "id_type": "feide_user_id",
            "id_value": "a6733d24-8987-44b6-8cd0-308030710aa2",
        },
        {
            "id_type": "uid",
            "id_value": "foo@bar.org",
        },
        {
            "id_type": "nin",
            "id_value": "12128812345",
        },
    ]

    person = evalg.database.query.get_or_create(
        db_session, Person, **data)

    for identifier in identifiers:
        id_obj = PersonExternalId(
            person=person.id,
            id_type=identifier['id_type'],
            id_value=identifier['id_value']
        )
        person.identifiers.append(id_obj)

    db_session.add(person)
    db_session.flush()
    return person


def test_query_person_by_id(person_foo, client):
    """Test the person by id query."""
    variables = {'id': str(person_foo.id)}
    query = """
    query person($id: UUID!) {
        person(id: $id) {
            id
            displayName
            email
            identifiers {
                idType
                idValue
            }
        }
    }
    """
    execution = client.execute(query, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['person']
    assert str(person_foo.id) == response['id']
    assert person_foo.display_name == response['displayName']
    assert person_foo.email == response['email']

    foo_ids = {x.id_type: x.id_value for x in person_foo.identifiers}
    response_ids = {x['idType']: x['idValue']
                    for x in response['identifiers']}
    assert foo_ids == response_ids


@pytest.fixture
def persons(db_session):
    """Multiple persons fixture."""

    data = [
        {
            'email': 'foo@example.org',
            'display_name': 'Foo Foo',
        },
        {
            'email': 'bar@example.org',
            'display_name': 'Bar Bar',
        },
    ]

    identifiers = [
        [
            {
                "id_type": "feide_id",
                "id_value": "foo@bar.org",
            },
            {
                "id_type": "feide_user_id",
                "id_value": "a6733d24-8987-44b6-8cd0-308030710aa2",
            },
            {
                "id_type": "uid",
                "id_value": "foo",
            },
            {
                "id_type": "nin",
                "id_value": "12128812345",
            },
        ],
        [
            {
                "id_type": "feide_id",
                "id_value": "bar@baz.org",
            },
            {
                "id_type": "feide_user_id",
                "id_value": "a6733d24-8987-55b6-8cd0-308030710aa2",
            },
            {
                "id_type": "uid",
                "id_value": "bar",
            },
            {
                "id_type": "nin",
                "id_value": "12128812346",
            },
        ]
    ]

    persons = [evalg.database.query.get_or_create(
        db_session, Person, **x) for x in data]

    for i, person in enumerate(persons):

        for identifier in identifiers[i]:
            id_obj = PersonExternalId(
                person=person.id,
                id_type=identifier['id_type'],
                id_value=identifier['id_value']
            )
            person.identifiers.append(id_obj)

        db_session.add(person)
    db_session.flush()

    return {str(x.id): x for x in persons}


def test_query_persons(persons, client):
    """Test the persons query."""
    query = """
    query persons {
        persons {
            id
            displayName
            email
            identifiers {
                idType
                idValue
            }
        }
    }
    """
    execution = client.execute(query)
    assert not execution.get('errors')
    response = execution['data']['persons']
    print(response)

    assert len(response) == len(persons)

    for person in response:
        assert person['id'] in persons
        assert persons[person['id']].display_name == person['displayName']
        assert persons[person['id']].email == person['email']

        fixture_ids = {
            x.id_type: x.id_value for x in persons[person['id']].identifiers}
        response_ids = {x['idType']: x['idValue']
                        for x in person['identifiers']}

        assert fixture_ids == response_ids
