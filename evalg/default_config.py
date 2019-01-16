#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Default configuration for eValg. """

DEBUG = False

LANGUAGES = {
    'en': 'English',
    'nb': 'Norwegian (bokmål)',
    'nn': 'Norwegian (nynorsk)'
}

APISPEC_TITLE = 'evalg'
APISPEC_VERSION = 'v1'

LOGGER_NAME = 'evalg'

LOGGING = {
    'disable_existing_loggers': False,
    'version': 1,
    'loggers': {
        '': {
            'handlers': ['stream_stderr'],
            'level': 'DEBUG',
        },
        'evalg': {
            'handlers': ['stream_stderr'],
            'level': 'DEBUG',
        },
        'watchdog': {
            'handlers': ['stream_stderr'],
            'level': 'WARNING'
        }
    },
    'formatters': {
        'default': {
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'class': 'logging.Formatter',
            'format': '%(asctime)s - %(request_id).8s - %(levelname)s - %(name)s - %(message)s'
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
            '()': 'evalg.request_id.RequestIdFilter'
        }
    }
}
