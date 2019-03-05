.. highlight:: bash

Local dev-environment
=====================

#. Set up a virtualenv with all the evalg dependencies.
#. Create an empty database.
#. Create a configuration file (``./instance/evalg_config.py``).
#. Initialize the database with the evalg schema.


Virtualenv
----------

::

  python -m venv /path/to/env
  source /path/to/env/bin/activate
  pip install -r requirements.txt


Database
--------
You'll need a database to run evalg.  In increasing complexity, you can:

#. Run a postgresql docker container
#. Install and run postgresql

.. todo::
   Describe *short* what needs to be done to set up a database, how to configure
   the database connection, and how to apply the schema and basic data?


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

The database is initialized by running

::

  FLASK_APP=evalg.wsgi flask db migrate
  FLASK_APP=evalg.wsgi flask db upgrade

.. note::
   After the initial release of evalg, you should skip the ``flask db migrate``
   commands, as the migrate scripts should be included in the evalg package.


The database can be populated by test fixture data by running:

::

  FLASK_APP=evalg.wsgi flask populate-tables

The database can later be reset by running:

::
  FLASK_APP=evalg.wsgi flask recreate-tables
  FLASK_APP=evalg.wsgi flask populate-tables

.. warning::
   Using ``recreate-tables`` can introduce conflicts with the database migration
   tool if you:

   - run it on an empty database without a schema
   - run it when you've done changes to the schema


Get the front-end up and running
--------------------------------
TODO: Link to front-end documentation.
