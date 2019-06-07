#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" eValg logging. """
import collections
import logging
import logging.config

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

try:
    import pythonjsonlogger.jsonlogger
    has_jsonlogger = True
except ImportError:
    has_jsonlogger = False


default_config = {
    'disable_existing_loggers': False,
    'version': 1,
    'loggers': {
        '': {
            'handlers': ['stream_stderr'],
            'level': 'DEBUG',
        },
        'evalg': {
            'propagate': True,
            'level': 'DEBUG',
        },
        'watchdog': {
            'handlers': ['stream_stderr'],
            'level': 'WARNING',
        }
    },
    'formatters': {
        'default': {
            'class': '{}.SafeFormatter'.format(__name__),
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'format': ('%(asctime)s - %(request_id).8s - '
                       '%(levelname)s - %(name)s - %(message)s'),
        },
    },
    'handlers': {
        'stream_stderr': {
            'formatter': 'default',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stderr',
            'filters': ['request_id', ],
        },
    },
    'filters': {
        'request_id': {
            '()': 'evalg.request_id.RequestIdFilter',
        }
    }
}


class ContextFilter(logging.Filter):
    """ Log filter that adds a static field to a record. """

    def __init__(self, field, value):
        self.field = field
        self.value = value

    def filter(self, record):
        setattr(record, self.field, self.value)
        return True


class LogContext(object):
    """
    A context that adds ContextFilters to a logger.

    Example usage:
        logger = logging.getLogger('example')
        with LogContext(logger, foo='bar'):
            # log records logged within the context will have a 'foo' set
            pass
    """

    def __init__(self, logger, **context):
        self.logger = logger
        self.filters = [ContextFilter(k, context[k]) for k in context]

    def __enter__(self):
        for f in self.filters:
            self.logger.addFilter(f)
        return self.logger

    def __exit__(self, *args, **kwargs):
        for f in self.filters:
            self.logger.removeFilter(f)


class SafeRecord(logging.LogRecord, object):
    """ A LogRecord wrapper that returns None for unset fields. """

    def __init__(self, record):
        self.__dict__ = collections.defaultdict(lambda: None, record.__dict__)


class SafeFormatter(logging.Formatter):
    """ A Formatter that use SafeRecord to avoid failure. """

    def format(self, record):
        record = SafeRecord(record)
        return super(SafeFormatter, self).format(record)


if has_jsonlogger:
    class SafeJsonFormatter(
            SafeFormatter,
            pythonjsonlogger.jsonlogger.JsonFormatter):
        """ A log formatter that formats SafeRecords as a JSON string. """
        pass


_lname = logging.getLevelName


def get_default_level(app):
    app_debug = app.config.get('DEBUG', app.debug)
    return logging.DEBUG if app_debug else logging.INFO


def configure_logging(dict_config=None):
    if dict_config is None:
        dict_config = default_config
    logging.config.dictConfig(dict_config)


def configure_sentry(config):
    """Configures and initializes Sentry."""
    if not config.get('enable', False):
        return
    dsn = config.get('dsn')
    if not dsn:
        raise Exception('Missing Sentry DSN')

    name_to_integration = {
        'logging': LoggingIntegration,
        'flask': FlaskIntegration,
    }

    integrations = []

    for name, kwargs in config.get('integrations', {}).items():
        if not kwargs.pop('enable', False):
            continue
        klass = name_to_integration.get(name)
        integrations.append(klass(**kwargs))

    sentry_sdk.init(
        dsn=dsn,
        integrations=integrations,
        default_integrations=True,
    )


def init_logging(app):
    """ Init logging.

    Loads log config from ``app.config['LOGGING']``
    """
    app.logger  # this makes flask create its logger
    root_logger = logging.getLogger()
    default_level = get_default_level(app)

    configure_logging(dict_config=app.config.get('LOGGING'))

    for logger in (app.logger, root_logger):
        if logger.level <= logging.NOTSET:
            logger.setLevel(default_level)

    configure_sentry(app.config.get('SENTRY'))
    print("Logging: flask={flask_level} root={root_level}"
          .format(flask_level=_lname(app.logger.getEffectiveLevel()),
                  root_level=_lname(root_logger.getEffectiveLevel())))
