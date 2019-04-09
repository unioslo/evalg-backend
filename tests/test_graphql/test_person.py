"""Tests the person related queries."""

import pytest


def test_query_person_by_id(persons, client):
    """Test the person by id query."""
    person_foo = next(iter(persons.values()))
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
