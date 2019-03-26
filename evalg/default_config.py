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
