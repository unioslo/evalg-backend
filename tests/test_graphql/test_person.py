"""Tests the person related queries."""


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


def test_query_persons(persons, client, logged_in_user):
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

    for person_id, person in persons.items():
        response_person = filter(
            lambda p: p['id'] == person_id, response
        ).__next__()
        print(response_person)
        assert(person.display_name == response_person['displayName'])
        assert(person.email == response_person['email'])
        fixture_ids = {
            x.id_type: x.id_value for x in person.identifiers}
        response_ids = {x['idType']: x['idValue']
                        for x in response_person['identifiers']}
        assert fixture_ids == response_ids
