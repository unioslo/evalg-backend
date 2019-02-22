"""Upload census file API."""
import collections
import logging

import flask
import flask_apispec
import flask_apispec.views
from flask import request

import evalg
import evalg.models.person
import evalg.database.query
from evalg.api import BadRequest
from evalg.file_parser.parser import CensusFileParser
from evalg.proc.pollbook import ElectionVoterPolicy

bp = flask.Blueprint('upload', __name__)
logger = logging.getLogger(__name__)


def get_or_create_person(id_type, id_value):
    """Get or create a Person entity."""
    try:
        person_identifier = evalg.database.query.lookup(
            evalg.db.session,
            evalg.models.person.PersonExternalId,
            id_type=id_type,
            external_id=id_value)
        return person_identifier.person
    except evalg.database.query.TooFewError:
        p = evalg.models.person.Person()
        p.external_ids.append(
            evalg.models.person.PersonExternalId(
                id_type=id_type,
                external_id=id_value))
        # Temporary hack -- set display_name
        p.display_name = {
            'nin': 'fnr: {0:.6}*****',
        }.get(id_type, id_type + ': {0}').format(id_value)
        evalg.db.session.add(p)
        evalg.db.session.flush()
        logger.info('created person=%s', repr(p))
        return p


class UploadCensusFile(flask_apispec.views.MethodResource):
    """Upload and parse census file."""

    @flask_apispec.doc(summary="Upload a file")
    def post(self, **kwargs):
        voters = ElectionVoterPolicy(evalg.db.session)
        result = collections.Counter(ok=0, failed=0)

        if 'pollbook_id' in request.form:
            pollbook_id = request.form['pollbook_id']
        else:
            raise BadRequest('missing pollbook_id')

        if 'census_file' in request.files:
            census_file = request.files['census_file']
        else:
            raise BadRequest('missing census_file')

        try:
            pollbook = evalg.database.query.lookup(
                evalg.db.session,
                evalg.models.pollbook.PollBook,
                id=pollbook_id)
        except Exception as e:
            raise BadRequest('No pollbook with id %r' % (pollbook_id,))

        census_file = request.files['census_file']
        if not census_file or census_file.filename == '':
            raise BadRequest('No census file provided')
        logger.info('updating %r from %r', pollbook, census_file)
        parser = CensusFileParser.factory(census_file)
        if not parser:
            raise BadRequest('Unsupported file %r' % (census_file.filename, ))
        id_type = parser.id_type
        logger.debug('loading file using parser %r (id_type=%r)',
                     type(parser), id_type)
        for i, identifier in enumerate(parser.parse(), 1):
            try:
                person = get_or_create_person(id_type, identifier)
            except Exception as e:
                logger.debug('entry #%d: unable to add person',
                             i, exc_info=True)
                result['failed'] += 1
                continue

            try:
                voters.add_voter(pollbook, person, manual=False)
            except Exception as e:
                logger.debug('entry #%d: unable to add voter: %s', i, e)
                result['failed'] += 1
                continue
            result['ok'] += 1

        evalg.db.session.commit()
        return flask.jsonify(result)


bp.add_url_rule(
    "/upload/",
    view_func=UploadCensusFile.as_view("UploadCensusFile"),
    methods=["POST"])


def init_app(app):
    app.register_blueprint(bp)
