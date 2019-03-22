Configuring evalg
=================

Instance folder
---------------
We load all evalg configuration files from the Flask app instance folder.  By
default, the instance folder is:

- ``./instance`` when running evalg directly from the repo.
- ``<sys-prefix>/evalg-instance`` when running evalg from an installed package.

The environment variable ``EVALG_CONFIG`` can be used to override the location
of the instance folder.


Configuration files
-------------------

evalg_config.py
~~~~~~~~~~~~~~~
The main evalg configuration gets loaded from ``evalg_config.py``. Any value in
this python file will override default values set in the
``evalg.default_config`` module.

.. todo::

   Document the config parameters.

Details on how to configure authentication is described in :doc:`auth`.


evalg_template_config.py
~~~~~~~~~~~~~~~~~~~~~~~~
The evalg template configuration defines election types and their rulesets.

.. todo::

   - Document election rulsets.
   - Consider moving this configuration into the database.
