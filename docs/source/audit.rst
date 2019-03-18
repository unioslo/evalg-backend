Audit documentation
===================


Introduction
------------

We use SQLAlchemy-Continuum to audit changes to the election data.
For more info see continuum_.

For each version table, a corresponding <table_name>_version is created.
If a row is altered, the old version will be save here, with a
transaction reference.

Transactions are stored in a separate transaction table.

Transaction model
-----------------

We use our own implementation of the base transaction model.

Changes:

* issued_at with time zone
* remote_addr uses a IP-addr type in SQLAlchemy.


Data saved per transaction
--------------------------

The user class functionality provided by Continuum to link
transactions to users.

We identify the user from the Dataporten authentication process.
Remote_addr is fetched from the flask request object.
The feide-id used in authentication is save as a key/value pair.

Transactions from cron/jobs ect. will not have a user/remote_addr.
The environment variable "EVALG_JOB_NAME" can be used to identify these.
If set, a key/value pair (job_name/<EVALG_JOB_NAME>) is automatically added.

Adding key/value pairs to transactions
--------------------------------------

The callback implementation of TransactionMetaPlugin can be used to add
arbitrary key/value pairs to a transaction.

.. code-block:: python

    @meta_plugin_source.register('foo')
    def get_bar():
        from foo include get_bar()
        return get_bar()

The key/value pair will be saved to transaction_meta if get_bar returns
a value::

 18 | foo | bar


Retrieving transactions
-----------------------

Transactions are queried like any other SQLAlchemy objects.

.. code-block:: python

    from evalg.models.election import Election
    from sqlalchemy_continuum import version_class


    ElectionVersion = version_class(Election)

    audit = db.session.query(ElectionVersion).filter_by(id='<uuid>').all()

    # Get the changes in a transaction
    log[0].changeset

    # Get the transaction
    log[3].transaction


.. _continuum: https://sqlalchemy-continuum.readthedocs.io
