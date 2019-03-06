Local dev-environment
=====================

#. Set up a virtualenv with all the evalg dependencies.
#. Create a configuration file (``./instance/evalg_config.py``).
#. Create and initialize a database with the evalg schema.
#. Run the flask app


Virtualenv
----------

.. code:: bash

  python -m venv /path/to/env
  source /path/to/env/bin/activate
  pip install -r requirements.txt


Configuration
-------------
Copy and update the example configuration files:

.. code:: bash

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


See :doc:`../config` for details on the evalg config, and :doc:`../auth` for
more information on how to configure mock authentication.


Database
--------

The database is initialized by running

.. code:: bash

  FLASK_APP=evalg.wsgi flask db migrate
  FLASK_APP=evalg.wsgi flask db upgrade

See :doc:`database` for more details on how to get a test database up and
running.


Run the app
-----------

.. code:: bash

   FLASK_APP=evalg.wsgi flask run


Get the front-end up and running
--------------------------------
TODO: Link to front-end documentation.
