import evalg

from flask import current_app
from sqlalchemy import and_


def create_person(username=None, fnr=None, feide_id=None):

    person = evalg.models.person.Person()
    if username:
        person.username = username
        person.first_name = "Username:"
        person.last_name = username
    elif fnr:
        person.nin = fnr
        person.first_name = "User from"
        person.last_name = "fnr"
    elif feide_id:
        person.feide_id = feide_id
        person.first_name = "Feide id"
        person.last_name = feide_id
    else:
        return None

    evalg.db.session.add(person)
    evalg.db.session.commit()
    current_app.logger.info(f"Created person {username} - {person}")
    return person

def get_or_create_person(identifyer, id_type):
    
    current_app.logger.info("Get person %s", identifyer)
    if id_type == 'username':
        current_app.logger.info("Get person, in username %s", identifyer)
        ret = evalg.models.person.Person.query.filter(
            evalg.models.person.Person.username == identifyer
        ).first()
        return ret if ret else create_person(username=identifyer)
    elif id_type == 'fnr':
        ret = evalg.models.person.Person.query.filter(
            evalg.models.person.Person.nin == identifyer
        ).first()
        return ret if ret else create_person(fnr=identifyer)
    elif id_type == 'feide_id':
        ret = evalg.models.person.Person.query.filter(
            evalg.models.person.Person.feide_id == identifyer
        ).first()
        return ret if ret else create_person(feide_id=id_type)
    else:
        return None


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
