"""This module implements methods for sending emails."""
from flask import current_app
from sentry_sdk import capture_exception

import evalg.mail.mailer


def send_vote_confirmation_mail(person, election_group):
    """Send an vote confirmation email to the user."""
    subject = 'Bekreftet mottatt stemme'

    try:
        election_group_name = election_group.name['nb']
        evalg.mail.mailer.send_mail(
            'vote_confirmation.tmpl',
            to_addr=person.email,
            electiongroup_name=election_group_name,
            subject=subject
        )
    except Exception as e:
        # Cache everything here to avoid that an error breaks the voting call.
        # Capture the exception and handle it in sentry.
        current_app.logger.info(e)
        capture_exception(e)
