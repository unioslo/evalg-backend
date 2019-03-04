"""
Alembic environment configuration.

The script is automatically imported by *alembic*, and is used to configure the
database migration tooling.   The environment requires an flask app context, so
any migration command must be invoked using *flask-migrate*:

::

    FLASK_APP=evalg flask db <command>

For more information:

- `Flask-Migrate Documentation
  <https://flask-migrate.readthedocs.io/en/latest/>`_
- `Alembic Documentation
  <https://alembic.sqlalchemy.org/en/latest/>`_
"""
import contextlib
import logging
import logging.config

from alembic import context
from flask import current_app
from sqlalchemy import engine_from_config, pool

logger = logging.getLogger(__name__)

target_metadata = current_app.extensions['migrate'].db.metadata
context.config.set_main_option(
    'sqlalchemy.url',
    current_app.config.get('SQLALCHEMY_DATABASE_URI'))


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = context.config.get_main_option('sqlalchemy.url')
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.readthedocs.org/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(context.config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    engine = engine_from_config(
        context.config.get_section(context.config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool)

    with contextlib.closing(engine.connect()) as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            user_module_prefix="evalg.database.types.",
            compare_type=True,
            compare_server_default=True,
            **current_app.extensions['migrate'].configure_args)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    logger.info("Offline mode")
    run_migrations_offline()
else:
    logger.info("Online mode")
    run_migrations_online()
