"""Commands for sending emails."""

import logging
import pytz

import click
import flask
import flask.cli

import evalg.mail.mailer

logger = logging.getLogger(__name__)


@click.command("send_status_mail", short_help="Send the election status report mail.")
@click.argument("to_addrs", nargs=-1)
@click.option(
    "--only_active_elections",
    default=False,
    is_flag=True,
    help="Only send email when there is active or upcoming elections.",
)
@flask.cli.with_appcontext
def send_status_mail(to_addrs, only_active_elections):
    """Send a status mail for the active elections."""
    import evalg.models

    election_groups = (
        evalg.db.session.query(evalg.models.election.ElectionGroup)
        .filter(evalg.models.election.ElectionGroup.deleted_at.is_(None))
        .all()
    )

    active_elections = [x for x in election_groups if x.status == "ongoing"]
    upcoming_elections = [x for x in election_groups if x.status == "published"]

    multiple_statuses = [x for x in election_groups if x.status == "multipleStatuses"]

    for election_group in multiple_statuses:
        election_status = [x.status for x in election_group.elections]
        if "ongoing" in election_status:
            active_elections.append(election_group)
        if "published" in election_status:
            upcoming_elections.append(election_group)

    if (
        only_active_elections
        and len(active_elections) == 0
        and len(upcoming_elections) == 0
    ):
        logger.info("No active or upcoming elections, skipping email.")
        return

    if only_active_elections:
        logger.info("Found active or upcoming elections, sending email.")

    tz = pytz.timezone("Europe/Oslo")
    active_elections_info = []
    for eg in active_elections:
        info = {"name": eg.name["nb"], "id": eg.id, "elections": []}

        for election in [e for e in eg.elections if e.active]:
            election_count = evalg.proc.vote.get_election_vote_counts(
                evalg.db.session, election
            )
            votes_in_census = election_count.get(
                "admin_added_auto_verified", 0
            ) + election_count.get("self_added_verified", 0)
            votes_rejected = election_count.get(
                "admin_added_rejected", 0
            ) + election_count.get("self_added_rejected", 0)
            votes_not_reviewed = election_count.get("self_added_not_reviewed", 0)
            votes_total = votes_in_census + votes_rejected + votes_not_reviewed
            election_voter_count = sum(
                [len(x.valid_voters) for x in election.pollbooks]
            )

            if election_voter_count == 0:
                election_turnout = 0.0
            else:
                election_turnout = (votes_in_census * 100) / election_voter_count

            election_info = {
                "id": election.id,
                "name": election.name["nb"],
                "start": election.start.astimezone(tz=tz),
                "end": election.end.astimezone(tz=tz),
                "voter_count": election_voter_count,
                "votes_total": votes_total,
                "votes_in_census": votes_in_census,
                "votes_rejected": votes_rejected,
                "votes_not_reviewed": votes_not_reviewed,
                "turnout": election_turnout,
                "pollbooks_info": [],
            }

            for pollbook in election.pollbooks:
                valid_pollbook_voters = len(pollbook.valid_voters)
                valid_pollbook_votes = len(pollbook.valid_voters_with_vote)

                if valid_pollbook_voters == 0:
                    pollbook_turnout = 0.0
                else:
                    pollbook_turnout = (
                        valid_pollbook_votes * 100
                    ) / valid_pollbook_voters

                pollbook_info = {
                    "name": pollbook.name,
                    "weight": pollbook.weight,
                    "valid_voters": valid_pollbook_voters,
                    "valid_votes": valid_pollbook_votes,
                    "turnout": pollbook_turnout,
                }
                election_info["pollbooks_info"].append(pollbook_info)

            info["elections"].append(election_info)
        info["voter_count"] = sum(x["voter_count"] for x in info["elections"])

        active_elections_info.append(info)

    root_node = (
        evalg.db.session.query(evalg.models.ou.OrganizationalUnit)
        .filter(evalg.models.ou.OrganizationalUnit.tag == "root")
        .first()
    )

    subject = "Valgstatus - eValg 3"
    if root_node:
        name = root_node.name["nb"]
        subject = f"Valgstatus - eValg 3 - {name}"
    else:
        logger.warning("Root node missing! Could not get institution name.")

    logger.info("Sending status mail to %s", ", ".join(to_addrs))
    evalg.mail.mailer.send_mail(
        template_name="status_report.tmpl",
        html_template_name="status_report_tmpl.html",
        to_addrs=to_addrs,
        subject=subject,
        active_elections=active_elections,
        upcoming_elections=upcoming_elections,
        active_elections_info=active_elections_info,
    )


commands = tuple((send_status_mail,))


def init_app(app):
    """Add commands to flask application cli."""
    for command in commands:
        app.cli.add_command(command)
