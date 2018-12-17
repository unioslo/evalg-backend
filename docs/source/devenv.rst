Development environment
=======================

A small development environment can be started with docker. This consists of
two containers, one for the database and one for the Flask-application.  The
Flask application auto-reloads its code when you edit files on your docker
host.

Start the development environment
---------------------------------

1. Create a config file:
   
::

 cp instance/evalg_config.py.example.dev instance/evalg_config.py

2. Star the docker containers using docker-compose:

::
   
 docker-compose -f docker-compose-evalg-dev.yaml up

3. Initialize the database:

::
   
 docker exec -it evalg_evalg_1 flask db init

4. Create appropriate database definitions (if the model has changed):

::

 docker exec -it evalg_evalg_1 flask db migrate

5. Apply said definitions: 

::

 docker exec -it evalg_evalg_1 flask db upgrade


To empty the database, run::

 docker exec -it evalg_evalg_1 flask db downgrade base


Add example data to the database
--------------------------------

If you want to populate the database with example data, run::

 docker exec -it evalg_evalg_1 flask populate-tables

Run the commands flask db downgrade and flask db upgrade on beforehand if you would like to clean before populating.


Example data definitions
~~~~~~~~~~~~~~~~~~~~~~~~

In evalg/fixtures, there are located a series of JSON files. These files define
the example data. These files must be mentioned in an appropriate order in
evalg/fixtures/populate_tables.py.

See also https://pypi.python.org/pypi/Flask-Fixtures for more details.

Alembic migration scripts
-------------------------

Alembic is used to upgrade the database on changes of the data model. Migration
data resides in the folder evalg/migrations, and can be generated with the
command flask db migrate, and applied with flask db upgrade.

Flask shell
-----------

You can run the flask shell in order to do migrations and run commands defined by the application::

 docker exec -it evalg_evalg_1 flask

Postgres client
---------------

If you should like to use psql::

 docker exec -u postgres -it evalg_db_1 psql

Flask Shell
-----------

The flask shell command also comes with a shell utility::

 FLASK_APP=evalg.wsgi flask shell

See http://flask.pocoo.org/docs/latest/shell/

Other CLI commands
------------------

This lists all CLI commands an application has to offer::

 FLASK_APP=evalg.wsgi flask --help




