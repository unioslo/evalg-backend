import pytest
import uuid

from sqlalchemy.exc import IntegrityError

import evalg.database.query
from evalg.models.voter import (Voter,
                                VERIFIED_STATUS_MAP,
                                VERIFIED_STATUS_NO_MAP)
from evalg.models.person import IdType


@pytest.fixture
def voter_foo(db_session, pollbook_one):
    data = {
        'id_type': IdType.feide_id,
        'id_value': 'foo@example.com',
        'pollbook_id': pollbook_one.id,
    }
    voter = evalg.database.query.get_or_create(
        db_session, Voter, **data)
    db_session.add(voter)
    db_session.flush()
    return voter


def test_voter_verification_status_valid(db_session, pollbook_foo):
    for self_added, reviewed, verified in VERIFIED_STATUS_MAP.keys():
        data = {
            'id_type': IdType('feide_id').value,
            'id_value': str(uuid.uuid4()) + '@example.com',
            'pollbook_id': pollbook_foo.id,
            'self_added': self_added,
            'reviewed': reviewed,
            'verified': verified,
        }
        voter = evalg.database.query.get_or_create(
            db_session, Voter, **data)
        db_session.add(voter)
        db_session.flush()
        assert voter.verified_status


def test_voter_verification_status_invalid(db_session, pollbook_foo):
    for self_added, reviewed, verified in VERIFIED_STATUS_NO_MAP:
        data = {
            'id_type': IdType('feide_id').value,
            'id_value': str(uuid.uuid4()) + '@example.com',
            'pollbook_id': pollbook_foo.id,
            'self_added': self_added,
            'reviewed': reviewed,
            'verified': verified,
        }
        voter = evalg.database.query.get_or_create(
            db_session, Voter, **data)
        db_session.add(voter)
        with pytest.raises(IntegrityError):
            db_session.flush()
        with pytest.raises(KeyError):
            voter.verified_status
        db_session.rollback()
