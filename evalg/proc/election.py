#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module implements election and election group maintenance.
"""
import aniso8601
import datetime
import functools

from flask import current_app
from sqlalchemy.sql import and_

from evalg.models.election import ElectionGroup, Election
from evalg.models.pollbook import PollBook
from evalg.models.election_list import ElectionList
from evalg.models.election_group_count import ElectionGroupCount
from evalg.utils import utcnow


def get_latest_election_group_count(session, group_id):
    latest_count = session.query(ElectionGroupCount).filter(
        and_(ElectionGroupCount.group_id == group_id)).order_by(
        ElectionGroupCount.initiated_at.desc()).first()

    return latest_count


def announce_group(session, group, **fields):
    """Announce an election group."""
    blockers = get_group_announcement_blockers(group)
    if blockers:
        # TODO: how to handle this in the above layer?
        raise Exception(blockers[0])
    group.announce()
    session.commit()
    return group


def unannounce_group(session, group, **fields):
    """Unannounce an election group."""
    group.unannounce()
    session.commit()
    return group


def get_group_announcement_blockers(group):
    """Check whether an election group can be announced."""
    blockers = []
    if group.announced:
        blockers.append('already-announced')
    for election in group.elections:
        if election.active:
            if missing_start_or_end(election):
                blockers.append('missing-start-or-end')
            if start_after_end(election):
                blockers.append('start-must-be-before-end')
    return blockers


def set_counting_method(session, election):
    if election.election_group.template_name in ('uio_principal',
                                                 'uio_dean',
                                                 'uio_department_leader'):
        if len(election.candidates) == 2:
            election.meta['counting_rules']['method'] = 'uio_mv'
        else:
            election.meta['counting_rules']['method'] = 'uio_stv'
    session.add(election)


def publish_group(session, group, **fields):
    """Publish an election group."""
    blockers = get_group_publication_blockers(group)
    if blockers:
        # TODO: how to handle this in the above layer?
        raise Exception(blockers[0])
    group.publish()
    session.commit()
    return group


def unpublish_group(session, group, **fields):
    """Unpublish an election group."""
    group.unpublish()
    session.commit()
    return group


def get_group_publication_blockers(group):
    """Check whether an election group can be published."""
    blockers = []
    if group.published:
        blockers.append('already-published')
    if not group.public_key:
        blockers.append('missing-key')
    for election in group.elections:
        if election.active:
            if missing_start_or_end(election):
                blockers.append('missing-start-or-end')
            if start_after_end(election):
                blockers.append('start-must-be-before-end')
    return blockers


def missing_start_or_end(election):
    return not election.start or not election.end


def start_after_end(election):
    if missing_start_or_end(election):
        return False
    return election.start > election.end


default_start_time = datetime.time(7, 0)
default_end_time = datetime.time(11, 0)
default_duration = datetime.timedelta(days=7)


def make_group_from_template(session, template_name, ou, principals=()):
    """Create election with elections from template"""
    current_app.logger.info('Make election group %s for %s',
                            template_name,
                            ou)
    election_templates = current_app.config.get('ELECTION_GROUP_TEMPLATES')

    # if current_app.config['AUTH_ENABLED'] and not \
    #        check_perms(principals, 'create-election', ou=ou):
    #    current_app.logger.info('Testing %s', principals)
    #    raise PermissionDenied()

    template = election_templates[template_name]
    name = template['name']
    group_type = template['settings']['group_type']
    elections = template['settings']['elections']
    metadata = template['settings']['rule_set']

    now = utcnow()

    def candidate_type(e):
        return metadata['candidate_type']

    def common_candidate_type():
        return functools.reduce(lambda x, y: x if x == y else None,
                                map(candidate_type, elections))

    def default_start():
        return datetime.datetime.combine(
            now.date(),
            default_start_time).replace(tzinfo=datetime.timezone.utc)

    def default_end():
        return datetime.datetime.combine(
            (now + default_duration).date(),
            default_end_time).replace(tzinfo=datetime.timezone.utc)

    def mandate_period_start(e):
        start = e['mandate_period'].get('start', '--01-01')

        if start.startswith('--'):
            # aniso8601 does not support extended year representation.
            # Let's try to fix that:
            start = str(now.year) + start[1:]

        date = aniso8601.parse_date(start)
        if date < now.date():
            date = date.replace(year=(now.year + 1))
        return date

    def mandate_period_end(e):
        start = mandate_period_start(e)
        length = e['mandate_period'].get('duration')
        if length is None:
            return None
        duration = aniso8601.parse_duration(length)
        return start + duration

    grp_name = dict()
    for lang in name.keys():
        grp_name[lang] = name[lang].format(ou.name[lang])

    group = ElectionGroup(name=grp_name,
                          template_name=template_name,
                          description=None,  # Set this?
                          type=group_type,
                          meta=metadata,
                          ou=ou)

    def make_candidate_list(name):
        cand_list = ElectionList(name=name)
        return cand_list

    def make_pollbook(kw):
        return PollBook(**kw)

    def make_election(e):
        if group_type == 'single_election':
            name = group.name
        else:
            name = e['name']
        election = Election(name=name,
                            sequence=e['sequence'],
                            election_group=group,
                            start=default_start(),
                            end=default_end(),
                            mandate_period_start=mandate_period_start(e),
                            mandate_period_end=mandate_period_end(e),
                            meta=metadata,
                            active=group_type == 'single_election', )
        if candidate_type(e) == 'party_list':
            election.lists = list()
        else:
            election.lists = [make_candidate_list(name)]
        election.pollbooks = list(map(make_pollbook, e['voter_groups']))
        return election

    group.elections = list(map(make_election, elections))
    session.add(group)
    session.flush()
    return group
