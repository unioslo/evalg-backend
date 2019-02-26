.. highlight:: bash

Configuring Evalg
=================

Configuration files
-------------------

Instance folder
~~~~~~~~~~~~~~~

.. note::

   This is only relevant when installing from the package.
   When running the development enviroment, the instance folder
   in the repo is used.

We store all configuration files in the flask instance folder.
We use the environment variables *EVALG_CONFIG* to set the path.

::

 export EVALG_CONFIG="/path/to/evalg/instance"

evalg_config.py
~~~~~~~~~~~~~~~

Main config file. Overrides default values in `evalg/default_config.py`.

.. todo::

   Document the config parameters.

evalg_template_config.py
~~~~~~~~~~~~~~~~~~~~~~~~

Defines the rulesets used by the various supported election.

.. todo::

   Document the election rulsets.



Configuring authentication and authorization with Dataporten
------------------------------------------------------------

Using a mock for Dataporten
~~~~~~~~~~~~~~~~~~~~~~~~~~~

During day-to-day development, it is easier to use a mock of Dataporten,
that assumes that all users of the application is logged in and maps
their identity to a faux user.

The following configuration snippet enables mocking authentication::

  AUTH_ENABLED = True

  AUTH_METHOD = 'feide_mock'

  # when mocking, pretend the gatekeeper authenticated this user
  FEIDE_MOCK_LOGIN_AS = 'abababab-abab-abab-abab-abababababab'
  FEIDE_MOCK_DATA = {
      'client_id': 'fafafafa-fafa-fafa-fafa-fafafafafafa',
      'users': {
          'abababab-abab-abab-abab-abababababab': {
              'id': 'abababab-abab-abab-abab-abababababab',
              'sec': {
                  'feide': ('testesen@example.com', ),
                  'nin': ('01011012343', ),
              },
              'feide_data': {
                  'givenName': 'Test',
                  'sn': 'Testesen',
                  'displayName': 'Test Testesen',
                  'eduPersonEntitlement': ('urn:mace:uio.no:evalg:valgadministrator', )
              }
          },
      },
  }

Actual Datporten integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To set up authentication with Dataporten, the following configuration should be defined::

  AUTH_ENABLED = True

  AUTH_METHOD = 'feide'
  FEIDE_BASIC_REQUIRE = True
  FEIDE_BASIC_USERS = [
      ('dataporten', '<password>'),
  ]

`<password>` should be replaced with the password supplied by the `Dataporten API Gateway <https://docs.feide.no/>`_.

