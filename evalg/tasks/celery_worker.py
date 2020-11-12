"""Different Celery-tasks for eValg"""
import datetime
import json
import logging

from werkzeug.local import LocalProxy

from sentry_sdk import capture_exception

import evalg.mail.mailer
import evalg.proc.pollbook
from evalg import create_app, db
from evalg.tasks.flask_celery import make_celery
from evalg.file_parser.parser import CensusFileParser

logger = logging.getLogger(__name__)
app = create_app()
celery = LocalProxy(lambda: make_celery(app))


@celery.task(bind=True)
def import_census_file_task(self, pollbook_id, census_file_id):
    """Import census-file functionality"""
    logger.info('Starting to import census file %s into pollbook %s (%s)',
                pollbook_id,
                census_file_id,
                self.request.id)
    census_file = db.session.query(
        evalg.models.census_file_import.CensusFileImport).get(census_file_id)

    pollbook = db.session.query(
        evalg.models.pollbook.Pollbook).get(pollbook_id)

    parser = CensusFileParser.factory(census_file.census_file,
                                      census_file.mime_type)

    id_type = parser.id_type
    voter_policy = evalg.proc.pollbook.CachedPollbookVoterPolicy(
        db.session, pollbook)

    logger.debug('Loading file using parser %r (id_type=%r)',
                 type(parser), id_type)
    results = {
        'added_nr': 0,
        'already_in_pollbook_nr': 0,
        'already_in_pollbook': [],
        'error_nr': 0,
        'error': [],
    }
    voters = []
    for i, id_value in enumerate(parser.parse(), 1):
        try:
            voter = voter_policy.create_voter(
                id_type, id_value, self_added=False)
            if voter and voter not in voters:
                results['added_nr'] += 1
                logger.info('Entry #%d: Added voter to pollbook: %s',
                            i, pollbook_id)
                voters.append(voter)
            else:
                logger.info('Entry #%d: Voter exists in pollbook: %s',
                            i, pollbook_id)
                results['already_in_pollbook_nr'] += 1
                results['already_in_pollbook'].append(id_value)

        except Exception as e:
            capture_exception(e)  # overkill?
            logger.warning('Entry #%d: unable to add voter: %s',
                           i, e, exc_info=True)
            results['error_nr'] += 1
            results['error'].append(id_value)
            continue

    db.session.add_all(voters)
    db.session.commit()

    census_file.finished_at = datetime.datetime.now(datetime.timezone.utc)
    census_file.import_results = json.dumps(results)
    db.session.add(census_file)
    db.session.commit()
    logger.info('Finished importing census file %s into pollbook %s (%s)',
                pollbook_id,
                census_file_id,
                self.request.id)


@celery.task(bind=True,
             autoretry_for=(Exception,),
             exponential_backoff=60,
             retry_kwargs={'max_retries': 10},
             retry_jitter=True)
def send_vote_confirmation_mail_task(self, email_addr, election_group_name):
    """Send an vote confirmation mail to the user."""
    logger.info('Starting send vote confirmation mail task. '
                'email: %s, election_name: %s',
                email_addr, election_group_name)
    subject = 'Bekreftet mottatt stemme'

    evalg.mail.mailer.send_mail(
        template_name='vote_confirmation.tmpl',
        to_addrs=[email_addr],
        electiongroup_name=election_group_name,
        subject=subject,
        voter_id=email_addr
    )
    logger.info('Send vote confirmation mail task done. '
                'email: %s, election_name: %s',
                email_addr, election_group_name)
