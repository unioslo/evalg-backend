.. highlight:: bash

Development environment
=======================

#. Set up a virtualenv with all the evalg dependencies.
#. Create an empty database.
#. Create a configuration file (``./instance/evalg_config.py``).
#. Update the database with the evalg schema.

Virtualenv
----------

::

  python -m venv /path/to/env
  source /path/to/env/bin/activate
  pip install -r requirements.txt


Database
--------
TODO: Describe *short* what needs to be done to set up a database, how to
configure the database connection, and how to apply the schema and basic data.

1. Install postgresql...
2. Configure postgresql...
3. Start postgresql...

TODO: Link to more substantial documentation about the database setup.


Configuration
-------------
Copy and update the example configuration files:

::

  cp instance/evalg_template_config.py.example instance/evalg_template_config.py
  cp instance/evalg_config.py.example.dev instance/evalg_config.py
  $EDITOR instance/evalg_config.py


You'll typically have to configure:

::

  SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/evalg'
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  LOGGER_NAME = 'evalg'

  AUTH_ENABLED = True
  AUTH_METHOD = 'feide_mock'
  FEIDE_MOCK_LOGIN_AS = …
  FEIDE_MOCK_DATA = {
      'client_id': …,
      'users': { … },
   }


See :ref:`doc-config` for details on the evalg config, and :ref:`doc-auth` for
more information on how to configure mock authentication.

Database init
-------------

::

  FLASK_APP=evalg.wsgi flask recreate-tables
  FLASK_APP=evalg.wsgi flask populate-tables


.. note::
   recreate-tables is incompatible with the database migration commands.

   To support database migrations, you'll have to use ``flask db migrate`` and
   ``flask db upgrade``.


Get the front-end up and running
--------------------------------
TODO: Link to front-end documentation.
