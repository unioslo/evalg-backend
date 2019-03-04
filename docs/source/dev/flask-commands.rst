Flask commands
==============

flask shell
-----------
Running ``flask shell`` will start `IPython`_ with some extra items in the shell
``globals()``:

.. code:: bash

   FLASK_APP=evalg.wsgi flask shell

See the `flask shell documentation`_ for more info.


flask import-units
------------------

The ``flask import-units`` command can be used to import OrganizationalUnits
from the University of Oslo HR/ERP system.

.. code:: bash

   FLASK_APP=evalg.wsgi flask import-units

To make this command work, you'll first have to add some configuration to
``evalg_config.py``:

::

   UNIT_IMPORTER = {
       'type': 'UIOSAPWS',
       'config': {
               'base_url': <URI>,
               'api_key': <SAP_API_KEY>,
           'root_ou': <ROOT_OU_NR>,
       }
   }


Other commands
--------------

This lists all CLI commands an application has to offer:

.. code:: bash

   FLASK_APP=evalg.wsgi flask --help


.. _IPython: https://ipython.org/
.. _flask shell documentation: http://flask.pocoo.org/docs/latest/shell/
