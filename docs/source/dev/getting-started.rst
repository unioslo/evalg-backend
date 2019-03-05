Getting started with evalg
==========================

Codestyle
---------

Codestyle is not strictly enforced.

* Write pretty code
* Never use tab indents in python code
* Follow PEPs to the best of your ability (`PEP-8`_, `PEP-257`_)
* Docstrings should work with `sphinx`_

Apply all the linters! This author recommends running ``flake8`` with plugins:
``naming``, ``pycodestyle``, ``pyflakes``.


Testing
-------

Testing in evalg is done using the *pytest* framework along with *pytest-flask*
and several other extensions.

- Unit tests live under the ``tests/`` directory
- Tests run using `pytest`_, typically invoked using `tox`_

::

   # Run tests using tox
   tox
   python -m tox

   # Run tests using pytest
   pytest
   python -m pytest


Versioning
----------

Versioning is done by tagging git commits and is automatically picked up by
`setuptools_scm`_.

.. note::

   The first stable release of this software will become evalg v3.0, as v2.x
   refers to an older implementation of electronic voting.

Version tags should start with the letter v (for version), and then follow the
syntax of `PEP-440`_, normally vX.Y.Z, where here X, Y and Z are numbers, Y and
Z being optional. Optionally, we can use the «aN», «bN» or «rcN» and the other
possibilities in PEP-440. Versions should follow semantic versioning guidelines.


Contribution guidelines
-----------------------

TODO: Make a ``CONTRIBUTE.rst`` in the root, and include?


References
----------
* About `GraphQL`_

3rd party documentation
~~~~~~~~~~~~~~~~~~~~~~~

* `graphene`_
* `flask`_
* `sqlalchemy`_


.. References
.. ----------
.. _flake-8: http://flake8.pycqa.org/
.. _flask: http://flask.pocoo.org/docs/
.. _graphene: https://docs.graphene-python.org/
.. _GraphQL: https://graphql.org/learn/
.. _pep-8: https://www.python.org/dev/peps/pep-0008/
.. _pep-257: https://www.python.org/dev/peps/pep-0257/
.. _pep-440: https://www.python.org/dev/peps/pep-0440/
.. _pytest: https://docs.pytest.org/
.. _setuptools_scm: https://github.com/pypa/setuptools_scm
.. _sphinx: http://www.sphinx-doc.org/
.. _sqlalchemy: https://docs.sqlalchemy.org/
.. _tox: https://tox.readthedocs.io/
