""" Default configuration for eValg. """

#
# Flask settings
#
from typing import Dict, List


DEBUG = False

#
# Database settings
#
SQLALCHEMY_DATABASE_URI = ""
SQLALCHEMY_TRACK_MODIFICATIONS = False

#
# Configuration for logging.config.dictConfig()
#
# The default is specified in `evalg.logging.default_config`, and is only
# included here for documentation purposes.
#

# LOGGING = {
#     'disable_existing_loggers': False,
#     'version': 1,
#     'loggers': {},
#     'handlers': {},
#     'formatters': {},
#     'filters': {},
# }


# Enable email notifications
MAIL_ENABLE = False
MAIL_SMTP_SERVER = "localhost"
MAIL_SMTP_PORT = 25
MAIL_FROM_ADDR = ""
MAIL_REPLY_TO_ADDR = ""

#
# SAPWS config used to import organizational units.
#
SAPWS_BASE_URL = ""
SAPWS_API_KEY = ""
SAPWS_ROOT_OU = ""

#
# Configuration of feide_flask_gk.proxyfix
#
TRUSTED_PROXIES = (
    # Loopback
    "127.0.0.0/8",
    "::1",
)

#
# Feide auth configuration
#
AUTH_ENABLED = True
AUTH_METHOD = "feide"

FEIDE_BASIC_REQUIRE = True
FEIDE_BASIC_REALM = None
FEIDE_BASIC_USERS: List = []

#
# Permissions
#
# Defines what method should be used for checking that the user has access to
# a field on an SQLAlchemyObjectType.
PERMISSIONS = {
    "ElectionGroup": {
        "name": "allow",
        "description": "allow",
        "type": "allow",
        "meta": "allow",
        "ou_id": "allow",
        "elections": "allow",
        "active": "allow",
        "public_key": "can_manage_election_group",
        "announced_at": "allow",
        "published_at": "allow",
        "cancelled_at": "allow",
        "deleted_at": "can_manage_election_group",
        "announced": "allow",
        "published": "allow",
        "cancelled": "allow",
        "deleted": "allow",
        "status": "allow",
        "election_group_counts": "can_manage_election_group",
        "publication_blockers": "can_manage_election_group",
        "roles": "can_manage_election_group",
    },
    "Election": {
        "name": "allow",
        "start": "allow",
        "end": "allow",
        "information_url": "allow",
        "contact": "allow",
        "mandate_period_start": "allow",
        "mandate_period_end": "allow",
        "group_id": "allow",
        "election_group": "allow",
        "description": "allow",
        "meta": "allow",
        "active": "allow",
        "announced_at": "allow",
        "published_at": "allow",
        "cancelled_at": "allow",
        "announced": "allow",
        "published": "allow",
        "cancelled": "allow",
        "deleted": "allow",
        "vote_count": "can_manage_election",
        "status": "allow",
        "pollbooks": "allow",
        "lists": "allow",
        "has_votes": "can_manage_election",
        "is_locked": "can_manage_election",
        "election_results": "can_manage_election",
    },
    "ElectionGroupCount": {
        "group_id": "can_access_election_group_count",
        "election_group": "can_access_election_group_count",
        "election_results": "can_access_election_group_count",
        "initiated_at": "can_access_election_group_count",
        "initiated_by": "can_access_election_group_count",
        "finished_at": "can_access_election_group_count",
        "audit": "can_access_election_group_count",
        "status": "can_access_election_group_count",
    },
    "ElectionResult": {
        "election_id": "can_access_election_result",
        "election": "can_access_election_result",
        "election_group_count_id": "can_access_election_result",
        "election_group_count": "can_access_election_result",
        "election_protocol": "can_access_election_result",
        "ballots": "can_access_election_result",
        "ballots_with_metadata": "can_access_election_result",
        "result": "can_access_election_result",
        "pollbook_stats": "can_access_election_result",
        "election_protocol_text": "can_access_election_result",
    },
    "ElectionList": {
        "name": "allow",
        "description": "allow",
        "information_url": "allow",
        "election_id": "allow",
        "election": "allow",
        "candidates": "allow",
    },
    "Candidate": {
        "list_id": "allow",
        "list": "allow",
        "name": "allow",
        "meta": "allow",
        "information_url": "allow",
        "priority": "allow",
        "pre_cumulated": "allow",
        "user_cumulated": "allow",
    },
    "Person": {
        "email": "can_view_person",
        "display_name": "can_view_person",
        "last_update": "can_view_person",
        "last_update_from_feide": "can_view_person",
        "principal": "can_view_person",
        "identifiers": "can_view_person",
    },
    "PersonIdentifier": {
        "person_id": "can_view_person_ids",
        "id_type": "can_view_person_ids",
        "id_value": "can_view_person_ids",
        "person": "can_view_person_ids",
    },
    "Voter": {
        "id_type": "can_view_voter",
        "id_value": "can_view_voter",
        "pollbook_id": "can_view_voter",
        "pollbook": "can_view_voter",
        "self_added": "can_view_voter",
        "reviewed": "can_view_voter",
        "verified": "can_view_voter",
        "votes": "can_view_voter",
        "reason": "can_view_voter",
        "verified_status": "can_view_voter",
        "person": "can_view_voter",
        "has_voted": "can_view_voter",
    },
    "MasterKey": {
        "active": "allow",
        "created_at": "allow",
        "description": "allow",
        "public_key": "allow",
    },
    "Vote": {
        "voter_id": "can_view_vote",
        "ballot_id": "can_view_vote",
        "voter": "can_view_vote",
        "record": "can_view_vote",
    },
    "Pollbook": {
        "name": "allow",
        "weight": "can_manage_pollbook",
        "priority": "can_manage_pollbook",
        "election_id": "allow",
        "election": "allow",
        "voters": "can_manage_pollbook",
        "self_added_voters": "can_manage_pollbook",
        "admin_added_voters": "can_manage_pollbook",
        "verified_voters_count": "can_manage_pollbook",
        "verified_voters_with_votes_count": "can_manage_pollbook",
        "voters_with_vote": "can_manage_pollbook",
        "voters_without_vote": "can_manage_pollbook",
        "census_file_imports": "can_manage_pollbook",
        "nr_of_voters": "can_manage_pollbook",
        "voter_dump": "can_manage_pollbook",
        "voter_objects": None,
    },
    "CensusFileImport": {
        "pollbook_id": "can_manage_census_file_upload",
        "pollbook": "can_manage_census_file_upload",
        "file_name": "can_manage_census_file_upload",
        "mime_type": "can_manage_census_file_upload",
        "import_results": "can_manage_census_file_upload",
        "initiated_at": "can_manage_census_file_upload",
        "finished_at": "can_manage_census_file_upload",
        "status": "can_manage_census_file_upload",
    },
    "ElectionKeyMeta": {
        "generated_at": "can_view_election_group_key_meta",
        "generated_by": "can_view_election_group_key_meta",
    },
    # Nobody has access, since it is not used for anything currently
    "Group": None,
}

#
# Feide entitlement to group mappings.
#

FEIDE_ENTITLEMENT_MAPPING_ENABLED = True

FEIDE_ENTITLEMENT_MAPPING: Dict = {
    "publisher": [],
    "global_admin": [],
}

#
# Ballot encryption/serialization
#
ENVELOPE_TYPE = "base64-nacl"
ENVELOPE_PADDED_LEN = 1000

#
# Sentry config
#
SENTRY = {
    "enable": False,
    "dsn": "",
    "environment": "unknown",
    "integrations": {
        "logging": {
            "enable": True,
            "level": "INFO",
            "event_level": "ERROR",
        },
        "flask": {"enable": True},
    },
}
