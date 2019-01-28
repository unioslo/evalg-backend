"""Upload census file API."""
from collections import Counter
from flask import Blueprint, request, jsonify
from flask_apispec.views import MethodResource
from flask_apispec import doc
from uuid import UUID

import evalg
from evalg.api import BadRequest
from evalg.file_parser.parser import CensusFileParser
from evalg.models_helper.models_helper import get_or_create_person, add_voter

bp = Blueprint('upload', __name__)


class UploadCensusFile(MethodResource):
    """Upload and parse census file."""

    @doc(summary="Upload a file")
    def post(self, **kwargs):

        if 'pollbook_id' in request.form and 'census_file' in request.files:
            pollbook_id = request.form['pollbook_id']
            try:
                UUID(pollbook_id, version=4)
            except ValueError:
                raise BadRequest('pollbook_id is not a valid UUID')

            pollbook = evalg.models.pollbook.PollBook.query.get(pollbook_id)
            if not pollbook:
                raise BadRequest('pollbook_id is not a valid pollbook')
            census_file = request.files['census_file']
            if not census_file or census_file.filename == '':
                raise BadRequest('No census file provided')
            parser = CensusFileParser.factory(census_file)
            if not parser:
                raise BadRequest('Could not create file parser')

            id_type = parser.id_type
            result = Counter(ok=0, failed=0)
            for identifier in parser.parse():

                person = get_or_create_person(identifier, id_type)
                if not person:
                    result['failed'] += 1
                    continue

                voter = add_voter(person, pollbook)
                if not voter:
                    result['failed'] += 1
                    continue
                result['ok'] += 1

            return jsonify(result)
        else:
            raise BadRequest('poolbook-id and/or cenus file missing')


bp.add_url_rule(
    "/upload/", view_func=UploadCensusFile.as_view("UploadCensusFile"), methods=["POST"]
)


def init_app(app):
    app.register_blueprint(bp)
