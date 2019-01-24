"""The upload census file API."""
from flask import Blueprint, request, jsonify
from flask_apispec.views import MethodResource
from flask_apispec import doc
from uuid import UUID

import evalg
from evalg.api import BadRequest
from evalg.file_parser.parser import CensusFileParser


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

            parser = CensusFileParser.factory(census_file, pollbook)

            if not parser:
                raise BadRequest('Could not create file parser')

            parser.parse()
            return jsonify(parser.get_parsing_result())
        else:
            raise BadRequest('poolbook-id and/or cenus file missing')


bp.add_url_rule(
    "/upload/", view_func=UploadCensusFile.as_view("UploadCensusFile"), methods=["POST"]
)


def init_app(app):
    app.register_blueprint(bp)
