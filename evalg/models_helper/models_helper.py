import evalg
import logging

from flask import current_app
from sqlalchemy import and_

logger = logging.getLogger(__name__)

def create_person(identifier, id_type):
    person = evalg.models.person.Person()
    if id_type == 'uid':
        person.display_name = 'Username: {0}'.format(identifier)
    elif id_type == 'nin':
        person.display_name = 'Fnr: {0}*****'.format(identifier[0:6])
    elif id_type == 'feide_id':
        person.display_name = 'Feide id: {0}'.format(identifier)
    else:
        return None

    new_id = evalg.models.person.PersonExternalId(
        person_id=person.id,
        id_type=id_type,
        external_id=identifier,
    )
    person.external_ids.append(new_id)

    evalg.db.session.add(person)
    evalg.db.session.commit()
    logger.info("Created person with id %s ", identifier)
    return person


def get_or_create_person(identifier, id_type):
    logger.info("Get person %s", identifier)
    ret = evalg.models.person.PersonExternalId.query.filter(
        and_(
            evalg.models.person.PersonExternalId.external_id == identifier,
            evalg.models.person.PersonExternalId.id_type == id_type,
        )
    ).first()

    if ret:
        return evalg.models.person.Person.query.get(ret.person_id)
    return create_person(identifier, id_type)


def add_voter(person, pollbook):
    voter = evalg.models.voter.Voter.query.filter(
        and_(
            evalg.models.voter.Voter.pollbook_id == pollbook.id,
            evalg.models.voter.Voter.person_id == person.id,
        )
    ).first()

    if voter:
        # Voter exist in pollbook
        return None

    voter = evalg.models.voter.Voter()
    voter.person_id = person.id
    voter.pollbook_id = pollbook.id
    voter.voter_status = evalg.models.voter.VoterStatus.query.get(
        "imported")
    evalg.db.session.add(voter)
    evalg.db.session.commit()

    return voter
