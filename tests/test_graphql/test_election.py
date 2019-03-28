import pytest

import evalg.database.query
from evalg.models.election import ElectionGroup


@pytest.fixture
def group_foo(db_session):
    data = {
        'name': {
            'nb': 'Foo',
            'en': 'Foo',
        },
        'type': 'single_election',
        'description': {
            'nb': 'Description foo',
            'en': 'Description foo',
        }
    }
    group = evalg.database.query.get_or_create(
        db_session, ElectionGroup, **data)
    db_session.add(group)
    db_session.flush()
    return group


def test_query_electiongroup_by_id(group_foo, client):
    variables = {'id': str(group_foo.id)}
    query = """
    query electionGroup($id: UUID!) {
        electionGroup(id: $id) {
            name
            description
        }
    }
    """
    execution = client.execute(query, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['electionGroup']
    assert group_foo.name == response['name']
    assert group_foo.description == response['description']
