""" Default configuration for eValg. """

#
# Flask settings
#
DEBUG = False

#
# Database settings
#
SQLALCHEMY_DATABASE_URI = ''
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


#
# SAPWS config used to import organizational units.
#
SAPWS_BASE_URL = ''
SAPWS_API_KEY = ''
SAPWS_ROOT_OU = ''

#
# Configuration of feide_flask_gk.proxyfix
#
TRUSTED_PROXIES = (
    # Loopback
    '127.0.0.0/8',
    '::1',
)

#
# Feide auth configuration
#
AUTH_ENABLED = True
AUTH_METHOD = 'feide'

FEIDE_BASIC_REQUIRE = True
FEIDE_BASIC_REALM = None
FEIDE_BASIC_USERS = []

#
# Permissions
#
PERMISSIONS = {
    'ObjectTypes': {
        'ElectionGroup': {
            'Fields': {
                'name': 'allow',
                'description': 'allow',
                'type': 'allow',
                'meta': 'allow',
                'ou_id': 'allow',
                'elections': 'allow',
                'active': 'allow',
                'public_key': 'can_manage_election_group',
                'announced_at': 'allow',
                'published_at': 'allow',
                'cancelled_at': 'allow',
                'deleted_at': 'can_manage_election_group',
                'announced': 'allow',
                'published': 'allow',
                'cancelled': 'allow',
                'deleted': 'allow',
                'status': 'allow',
                'election_group_counts': 'can_manage_election_group',
                'publication_blockers': 'can_manage_election_group',
                'roles': 'can_manage_election_group'
            }
        },
        'Election': {
            'Fields': {
                'name': 'allow',
                'start': 'allow',
                'end': 'allow',
                'information_url': 'allow',
                'mandate_period_start': 'allow',
                'mandate_period_end': 'allow',
                'group_id': 'allow',
                'election_group': 'allow',
                'description': 'allow',
                'meta': 'allow',
                'active': 'allow',
                'announced_at': 'allow',
                'published_at': 'allow',
                'cancelled_at': 'allow',
                'announced': 'allow',
                'published': 'allow',
                'cancelled': 'allow',
                'deleted': 'allow',
                'vote_count': 'can_manage_election',
                'status': 'allow',
                'pollbooks': 'allow',
                'lists': 'allow',
                'election_results': 'can_manage_election'
            }
        },
        'ElectionGroupCount': {
            'Fields': {
                'group_id': 'can_access_election_group_count',
                'election_group': 'can_access_election_group_count',
                'election_results': 'can_access_election_group_count',
                'initiated_at': 'can_access_election_group_count',
                'finished_at': 'can_access_election_group_count',
                'audit': 'can_access_election_group_count',
                'status': 'can_access_election_group_count',
            }
        },
        'ElectionResult': {
            'Fields': {
                'election_id': 'can_access_election_result',
                'election': 'can_access_election_result',
                'election_group_count_id': 'can_access_election_result',
                'election_group_count': 'can_access_election_result',
                'election_protocol': 'can_access_election_result',
                'ballots': 'can_access_election_result',
                'result': 'can_access_election_result',
                'pollbook_stats': 'can_access_election_result',
                'election_protocol_text': 'can_access_election_result',
            }
        },
        'ElectionList': {
            'Fields': {
                'name': 'allow',
                'description': 'allow',
                'information_url': 'allow',
                'election_id': 'allow',
                'election': 'allow',
                'candidates': 'allow',
            }
        },
        'Candidate': {
            'Fields': {
                'list_id': 'allow',
                'list': 'allow',
                'name': 'allow',
                'meta': 'allow',
                'information_url': 'allow',
                'priority': 'allow',
                'pre_cumulated': 'allow',
                'user_cumulated': 'allow',
            }
        }
    },

}

#
# Ballot encryption/serialization
#
ENVELOPE_TYPE = 'base64-nacl'
ENVELOPE_PADDED_LEN = 1000

#
# Sentry config
#
SENTRY = {
    'enable': False,
    'dsn': '',
    'integrations': {
        'logging': {
            'enable': True,
            'level': 'INFO',
            'event_level': 'ERROR',
        },
        'flask': {
            'enable': True
        }
    }
}
