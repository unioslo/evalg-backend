import json

import evalg

from evalg import db
from evalg.models.person import Person as PersonModel

from flask import current_app
from sqlalchemy import and_


class CensusFileParser(object):
    def __init__(self, census_file, pollbook):
        self.census_file = census_file
        self.pollbook = pollbook
        self.parsing_results = {
            "added_ok": 0,
            "added_failed": 0,
            "already_added": 0,
            "status": "",
        }
        self.persons = []

    def get_voters(self):
        return self.voters

    def get_parsing_result(self):
        return self.parsing_results

    def parse(self):
        raise NotImplementedError("parser method missing")

    def _get_or_create_person(self, username=None, fnr=None, feide_id=None):
        current_app.logger.info("Get person %s", username)
        if username:
            current_app.logger.info("Get person, in username %s", username)

            ret = evalg.models.person.Person.query.filter(
                evalg.models.person.Person.username == username
            ).first()
            return ret if ret else self._create_person(username=username)

        elif fnr:
            ret = evalg.models.person.Person.query.filter(
                evalg.modesl.person.Person.nin == fnr
            ).first()
            return ret if ret else self._create_person(fnr=fnr)

        elif feide_id:
            ret = evalg.models.person.Person.query.filter(
                evalg.modesl.person.Person.feide_id == feide_id
            ).first()
            return ret if ret else self._create_person(feide_id=feide_id)

        else:
            raise AttributeError("Id type not given")

    def _create_person(self, username=None, fnr=None, feide_id=None):

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
            raise AttributeError()

        db.session.add(person)
        db.session.commit()

        current_app.logger.info(f"Created person {username} - {person}")

        return person

    def _add_voter(self, person, pollbook):
        voter = evalg.models.voter.Voter.query.filter(
            and_(
                evalg.models.voter.Voter.pollbook_id == pollbook.id,
                evalg.models.voter.Voter.person_id == person.id,
            )
        ).first()

        if voter:
            # Voter exist in pollbook
            self.parsing_results["already_added"] += 1
            return

        voter = evalg.models.voter.Voter()
        voter.person_id = person.id
        voter.pollbook_id = pollbook.id
        voter.voter_status = evalg.models.voter.VoterStatus.query.get(
            "imported")
        db.session.add(voter)
        db.session.commit()

        self.parsing_results["added_ok"] += 1

    @classmethod
    def get_mime_type(cls):
        raise NotImplementedError("get_mime_type method missing")

    @classmethod
    def get_supported_mime_types(cls):
        return [x.get_mime_type() for x in CensusFileParser.__subclasses__()]

    @classmethod
    def factory(cls, census_file, pollbook):
        """Returns the correct file parser if supported."""
        supported_mime_types = {
            x.get_mime_type(): x for x in CensusFileParser.__subclasses__()
        }

        if not pollbook:
            return None

        if census_file.mimetype in supported_mime_types:
            return supported_mime_types[census_file.mimetype](
                census_file,
                pollbook)
        return None


class PlainTextParser(CensusFileParser):
    @classmethod
    def get_mime_type(cls):
        return "text/plain"

    def find_identifier_type(self, fields):

        # Check if fnr
        try:
            [int(x) for x in fields]
            if len(set([len(x) for x in fields]) - set([10, 11])) == 0:
                return "fnr"
        except ValueError:
            pass

        # Check if Feide ID
        if all(["@" in x for x in fields]):
            return "feide_id"

        # Assume username
        return "username"

    def parse(self):

        content = self.census_file.stream.read().decode("utf-8")

        fields = [x for x in content.split("\n") if x]
        id_type = self.find_identifier_type(fields)

        if id_type == "fnr":
            for fnr in fields:
                try:
                    int(fnr)
                except ValueError:
                    self.parser_results["person_failed"] += 1
                    continue

                if len(fnr) == 10:
                    # Probably missing a leading zero.
                    fnr = fnr.rjust(11, "0")

                elif len(fnr) < 10:
                    # Invalid fnr
                    self.parser_results["added_failed"] += 1
                    continue

                person = self._get_or_create_person(fnr=fnr)
                if person is None:
                    self.parser_results["added_failed"] += 1
                    continue

                self._add_voter(person, self.pollbook)

        elif id_type == "feide_id":
            for feide_id in fields:
                person = self._get_or_create_person(feide_id=feide_id)

                if not person:
                    self.parser_results["added_failed"] += 1
                    continue

                self._add_voter(person, self.pollbook)

        elif id_type == "username":
            for username in fields:
                person = self._get_or_create_person(username=username)

                if not person:
                    self.parser_results["added_failed"] += 1
                    continue

                self._add_voter(person, self.pollbook)
        else:
            return None
