import pytest

from evalg.authorization import (allows,
                                 PermissionDenied,
                                 IsElectionGroupAdmin)
from evalg.database.query import get_or_create
from evalg.models.authorization import (ElectionGroupRole,
                                        PersonPrincipal)


def test_IsElectionGroupAdmin_denies(db_session, logged_in_user, group_foo):
    with pytest.raises(PermissionDenied):
        allows.run([IsElectionGroupAdmin(election_group_id=group_foo.id)])


def test_IsElectionGroupAdmin_allows(db_session, logged_in_user, group_foo):
    principal = get_or_create(
        db_session,
        PersonPrincipal,
        person_id=logged_in_user.person.id)
    db_session.add(principal)
    db_session.flush()
    role = get_or_create(
        db_session,
        ElectionGroupRole,
        name='admin',
        group_id=group_foo.id,
        principal_id=principal.id)
    db_session.add(role)
    db_session.flush()
    allows.run([IsElectionGroupAdmin(election_group_id=group_foo.id)])
