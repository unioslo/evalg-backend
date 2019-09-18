"""Test election group related graphql queries and mutation."""
import pytest

from evalg.models.election import ElectionGroup
from evalg.graphql import get_context

# TODO, move all election group test here


@pytest.mark.parametrize(
    'template_name, expected_election_nr, election_type',
    [('uio_principal', 1, 'single_election'),
     ('uio_dean', 1, 'single_election'),
     ('uio_department_leader', 1, 'single_election'),
     ('uio_university_board', 4, 'multiple_elections'),
     ('uio_faculty_board', 4, 'multiple_elections'),
     ('uio_department_board', 4, 'multiple_elections'),
     ('uio_student_parliament', 1, 'single_election')]
)
def test_create_election_group_mutation(
        template_name,
        expected_election_nr,
        election_type,
        client,
        make_ou,
        logged_in_user):
    """Test the CreateNewElectionGroup mutation."""
    ou = make_ou(name='Test enhet')
    variables = {
        'ouId': str(ou.id),
        'template': True,
        'templateName': template_name
    }
    mutation = """
    mutation ($ouId: UUID!, $template: Boolean!, $templateName: String!) {
        createNewElectionGroup(ouId: $ouId,
                               template: $template,
                               templateName: $templateName) {
            ok
            electionGroup {
                id
                announced
                elections {
                    id
                    active
                }
                ouId
                publicKey
                published
                type
            }
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['createNewElectionGroup']
    assert response['ok']

    election_group = response['electionGroup']

    assert not election_group['announced']
    assert not election_group['published']
    assert election_group['ouId'] == str(ou.id)
    assert election_group['publicKey'] is None
    assert election_group['type'] == election_type

    assert len(election_group['elections']) == expected_election_nr
    for election in election_group['elections']:
        if election_type == 'multiple_elections':
            assert not election['active']
        else:
            assert election['active']

    election_group_db = ElectionGroup.query.get(election_group['id'])
    assert election_group_db
    assert not election_group_db.announced
    assert election_group_db.ou_id == ou.id
    assert not election_group_db.published


@pytest.mark.parametrize(
    'key, success',
    [
        # Valid base64 key
        ('bO1pw6/Bslji0XvXveSuVbe4vp93K1DcpqYgIxRhYAs=', True),
        # Base64 key with none ascii character
        ('bO1pw6/Bslji0XvXveæuVbe4vp93K1DcpqYgIxRhYAs=', False),
        # Base64 key missing one character
        ('bO1pw6/BsljiXvXveSuVbe4vp93K1DcpqYgIxRhYAs=', False),
        # Empty string
        ('', False),
        # None base64 string
        ('æøå', False),
    ]
)
def test_set_election_group_key_mutation(
        key,
        success,
        client,
        make_election_group_from_template,
        logged_in_user):
    """Test the SetElectionGroupKey mutation."""

    election_group = make_election_group_from_template(
        'set_key_test', 'uio_dean', logged_in_user)

    variables = {
        'id': str(election_group.id),
        'publicKey': key
    }
    mutation = """
    mutation ($id: UUID!, $publicKey: String!) {
        setElectionGroupKey(id: $id, publicKey: $publicKey) {
            success
            code
            message
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['setElectionGroupKey']

    assert response['success'] == success
    election_group_db = ElectionGroup.query.get(election_group.id)
    assert (election_group_db.public_key == key) == success
