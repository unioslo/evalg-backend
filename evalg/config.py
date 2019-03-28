#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Methods for configuring the eValg application. """

import os


def init_config(app, environ_name, default_file_name,
                config=None,
                config_file=None,
                default_config=None):
    """ Initialize app config.

    The default configuration is always loaded.
    Then the app config is loaded from the first available source:

    1. the object provided as ``config``, if not ``None``
    2. the file provided in``config_file``, if not ``None``
    3. the path set in the environment variable ``environ_name``
    4. ``app.instance_path``/``default_file_name``, if it exists

    """
    # Load default config
    if default_config:
        app.config.from_object(default_config)

    if config is not None:
        print('Config: Using provided config object')
        app.config.from_object(config)
    elif config_file is not None:
        read_config_from_file(app, config_file)
    else:
        if app.config.from_envvar(environ_name, silent=True):
            print("Config: Loading config from ${!s} ({!s})".format(
                environ_name, os.environ[environ_name]))
        if app.config.from_pyfile(default_file_name, silent=True):
            print("Config: Loading config from instance path ({!s})".format(
                os.path.join(app.instance_path, default_file_name)))


def read_config_from_file(app, config=None):
    """ Initialize app config by evaluating a file.

    Supported file types: .py .cfg .json
    """
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
