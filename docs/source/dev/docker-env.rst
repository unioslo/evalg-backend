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

3. :doc:`Initialize the database <database>`:

::

   docker exec -it evalg_evalg_1 flask db migrate
   docker exec -it evalg_evalg_1 flask db upgrade


Flask commands
--------------

You can run different :doc:`flask commands <flask-commands>` in the evalg
container using ``docker exec``.  If you e.g. want to start an ipython shell:

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
