#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" eValg logging. """

import logging
import logging.config


def init_logging(app):
    """ Init logging.

    Loads log config from ``app.config['LOGGING']``
    """
    app.logger  # this makes flask create its logger
    logging_config = app.config.get('LOGGING')

    if logging_config:
        logging.config.dictConfig(logging_config)

    # Set default logger level based on app debug setting
    if app.logger.level == logging.NOTSET:
        level = logging.DEBUG if app.debug else logging.INFO
        print(
            "Logging: Setting level to {!s}".format(
                logging.getLevelName(level)))
        app.logger.setLevel(level)
    else:
        print(
            "Logging: Level {!s}".format(
                logging.getLevelName(app.logger.getEffectiveLevel())))
