#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Default configuration for eValg. """

DEBUG = False

LOGGER_NAME = 'ballotbox'

LOGGING = {
    'disable_existing_loggers': False,
    'version': 1,
    'loggers': {
        '': {
            'handlers': ['stream_stderr'],
            'level': 'DEBUG',
        },
        'ballotbox': {
            'handlers': ['stream_stderr'],
            'level': 'DEBUG',
        },
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
