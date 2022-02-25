import pytest

from typing import Callable

from sqlalchemy.orm.scoping import scoped_session
from faker import Faker

from evalg.models.election_list import ElectionList
from evalg.models.candidate import Candidate

fake = Faker()


@pytest.fixture
def candidate_generator(
    db_session: scoped_session,
) -> Callable[[ElectionList, int], Candidate]:
    def candidate_generator(election_list, priority):
        candidate = Candidate(
            name=fake.name(),
            meta={"field_of_study": fake.job()},
            list=election_list,
            priority=priority,
            pre_cumulated=False,
        )
        return candidate

    return candidate_generator


@pytest.fixture
def election_list_in_order(
    db_session,
    candidate_generator,
    election_group_generator,
) -> ElectionList:
    election_group = election_group_generator(election_type="party_list")

    election_list = ElectionList(
        election=election_group.elections[0],
        name={"nb": "Test 123", "en": "Test 123"},
    )

    db_session.add(election_list)
    db_session.flush()

    for x in range(1, 6):
        db_session.add(candidate_generator(election_list, x))

    db_session.commit()

    return election_list
