Working with the evalg database
===============================

To run evalg, you'll need a database:

#. If you're using the docker-compose setup, you already have a database
#. If you're running evalg on your own host, you'll have to setup your own.

You can either:

#. Run a postgresql docker container
#. Install and run postgresql, and create a new, empty database


Initializing the database
-------------------------

The database is initialized by running

::

  flask db migrate
  flask db upgrade

.. note::
   After the initial release of evalg, you should skip the ``flask db migrate``
   command, as the migrate scripts should be included in the evalg package.


The database can be populated by test fixture data by running:

::

  flask populate-tables

The database can later be reset by running:

::

  flask recreate-tables
  flask populate-tables

.. warning::
   Using ``recreate-tables`` can introduce conflicts with the database migration
   tool if you:

   - run it on an empty database without a schema
   - run it when you've done changes to the schema


Database migrations
-------------------

The database migrations are handled by `alembic`_, and all interaction with
alembic commands are glued together with Flask and the evalg configuration using
`flask-alembic`_.

To perform a database upgrade, you would typically run:

::

   flask db upgrade


Migration scripts are python scripts in the ``evalg/migrations/versions/``
directory.

If you've done changes to the database schema, you'll have to create and run a
migration. To create a new migration, you need a revision number and a
migration script - these can be created for you by running:

::

   flask db revision -m 'add a table named foo'

This will create a template migration script where you can implement upgrade and
downgrade routines.

If you've simply added a table or column, you can use the *migrate* command to
automatically generate a migration script with suggestions for how to implement
upgrade and downgrade:

::

   flask db migrate -m 'added data models for bar'

Look over the script carefully, and fix any issues. Make sure to test both
upgrade and downgrade!

When you're confident that the migration works, and you've tested it carefully,
you simply add the new script to the repository.


Test data
---------

The ``flask populate-tables`` command inserts data from ``evalg/fixtures``.

::

  flask populate-tables

If you create new data models, please include example data for those models in
the form of fixtures.

.. todo:: Replace flask-fixtures with something good.


.. References
.. ----------
.. _alembic: https://alembic.sqlalchemy.org/
.. _flask-alembic: https://flask-alembic.readthedocs.io/
