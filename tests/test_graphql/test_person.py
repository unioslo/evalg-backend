"""Tests the person related queries."""

from evalg.graphql import get_context


def test_query_person_by_id(db_session, make_full_election, make_pollbook_vote,
                            make_pollbook_voter, persons, client,
                            logged_in_user):
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
    election_group = make_full_election('test_query_persons')
    pollbook_id = next(iter(election_group['pollbooks']))
    voter = make_pollbook_voter(
        person=person_foo,
        pollbook=election_group['pollbooks'][pollbook_id][0]
    )
    vote = make_pollbook_vote(pollbook_voter=voter)

    context = get_context()
    execution = client.execute(query, variables=variables, context=context)
    assert not execution.get('errors')
    response = execution['data']['person']
    assert str(person_foo.id) == response['id']
    assert person_foo.display_name == response['displayName']
    assert person_foo.email == response['email']

    foo_ids = {x.id_type: x.id_value for x in person_foo.identifiers}
    response_ids = {x['idType']: x['idValue']
                    for x in response['identifiers']}
    assert foo_ids == response_ids


def test_query_persons(db_session, make_full_election, make_pollbook_vote,
                       make_pollbook_voter, persons, client, logged_in_user):
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
    election_group = make_full_election('test_query_persons')
    pollbook_id = next(iter(election_group['pollbooks']))
    for person_id, person in persons.items():
        voter = make_pollbook_voter(
            person=person,
            pollbook=election_group['pollbooks'][pollbook_id][0]
        )
        vote = make_pollbook_vote(pollbook_voter=voter)

    context = get_context()
    execution = client.execute(query, context=context)
    assert not execution.get('errors')
    response = execution['data']['persons']

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
