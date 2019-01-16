#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Methods for configuring the eValg application. """

import os


def init_config(app, config, environ_name, default_file_name,
                default_config=None):
    """ Initialize app config.

    Loads app config from the first available source:

    1. ``config`` argument, if not ``None``
    2. the path set in the environment variable ``environ_name``
    3. ``app.instance_path``/``default_file_name``, if it exists

    """
    # Load default config
    if default_config:
        app.config.from_object(default_config)

    # Read config
    if config and os.path.splitext(config)[1] in ('.py', '.cfg'):
        # <config>.py, <config>.cfg
        if app.config.from_pyfile(config, silent=False):
            print("Config: Loading config from argument ({!s})".format(config))
    elif config and os.path.splitext(config)[1] == '.json':
        # <config>.json
        with open(config, 'r') as config_file:
            if app.config.from_json(config_file.read(), silent=False):
                print("Config: Loading config from argument ({!s})".format(
                    config))
    elif config:
        # <config>.<foo>
        raise RuntimeError(
            "Unknown config file format '{!s}' ({!s})".format(
                os.path.splitext(config)[1], config))
    else:
        if app.config.from_envvar(environ_name, silent=True):
            print("Config: Loading config from ${!s} ({!s})".format(
                environ_name, os.environ[environ_name]))
        if app.config.from_pyfile(default_file_name, silent=True):
            print("Config: Loading config from intance path ({!s})".format(
                os.path.join(app.instance_path, default_file_name)))
