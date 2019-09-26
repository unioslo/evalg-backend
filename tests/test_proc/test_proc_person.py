from evalg.database.query import get_or_create
from evalg.proc.person import search_persons


def test_search_persons(db_session, person_generator):

    person = person_generator()
    results = search_persons(db_session, person.display_name)
    assert results.count() == 1
