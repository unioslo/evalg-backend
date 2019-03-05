.. highlight:: bash

Docker dev-enviroment
=====================

A small development environment can be started with docker. This consists of two
containers, one for the database and one for the Flask-application.  The Flask
application auto-reloads its code when you edit files on your docker host.


Start the development environment
---------------------------------

1. Create a config file:

::

   cp instance/evalg_config.py.example.dev instance/evalg_config.py

2. Start the docker containers using docker-compose:

::

   docker-compose -f docker-compose-evalg-dev.yaml up

3. Initialize the database:

::

   docker exec -it evalg_evalg_1 flask db migrate
   docker exec -it evalg_evalg_1 flask db upgrade


Add example data to the database
--------------------------------

If you want to populate the database with example data, run:

::

   docker exec -it evalg_evalg_1 flask populate-tables


To clear out the database:

::

   docker exec -it evalg_evalg_1 flask recreate-tables



Flask shell
-----------

You can run the flask shell in order to do migrations and run commands defined by the application:

::

   docker exec -it evalg_evalg_1 flask shell


.. tip::
   Create an alias for running flask commands in the docker container: ``alias
   docker-flask='docker exec -it evalg_evalg_1 flask'``


Postgres client
---------------

If you should like to use psql:

::

   docker exec -u postgres -it evalg_db_1 psql

.. tip::
   Create an alias for running psql in the docker container: ``alias
   docker-psql='docker exec -u postgres -it evalg_db_1 psql'``
