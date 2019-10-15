import datetime
import json
import logging

from werkzeug.local import LocalProxy

import evalg.proc.pollbook
from evalg import create_app, db
from evalg.tasks.flask_celery import make_celery
from evalg.file_parser.parser import CensusFileParser
from evalg.models.privkeys_backup import MasterKey

logger = logging.getLogger(__name__)
app = create_app()
celery = LocalProxy(lambda: make_celery(app))


@celery.task
def import_census_file_task(pollbook_id, census_file_id):

    logger.info('Starting to import census file %s into pollbook %s',
                pollbook_id, census_file_id)
    census_file = db.session.query(
        evalg.models.census_file_import.CensusFileImport).get(census_file_id)

    pollbook = db.session.query(
        evalg.models.pollbook.Pollbook).get(pollbook_id)

    parser = CensusFileParser.factory(census_file.census_file,
                                      census_file.mime_type)

    id_type = parser.id_type
    voters = evalg.proc.pollbook.ElectionVoterPolicy(db.session)
    logger.debug('Loading file using parser %r (id_type=%r)',
                 type(parser), id_type)
    results = {
        'added_nr': 0,
        'already_in_pollbook_nr': 0,
        'already_in_pollbook': [],
        'error_nr': 0,
        'error': [],
    }
    for i, id_value in enumerate(parser.parse(), 1):

        try:
            voters.add_voter_id(pollbook, id_type, id_value,
                                self_added=False)
            results['added_nr'] += 1
        except ValueError:
            logger.info('Entry #%d: unable to add voter: %s')
            results['already_in_pollbook_nr'] += 1
            results['already_in_pollbook'].append(id_value)
            continue
        except Exception as e:
            logger.warning('Entry #%d: unable to add voter: %s',
                           i, e, exc_info=True)
            results['error_nr'] += 1
            results['error'].append(id_value)
            continue

        if i % 1000 == 0:
            db.session.commit()

    db.session.commit()

    census_file.finished_at = datetime.datetime.now(datetime.timezone.utc)
    census_file.import_results = json.dumps(results)
    db.session.add(census_file)
    db.session.commit()
    logger.info('Finished importing census file %s into pollbook %s',
                pollbook_id, census_file_id)
