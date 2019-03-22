Evalg 3 documentation
=====================

Evalg 3 is a re-implementation of the electronic voting system used at the
University of Oslo.

Background
----------

In 2006, the University of Oslo decided that its elections should be
electronic. For such, an web application was developed. Now (2017), this web
application is old, and it builds upon unmaintained frameworks. Therefore it
was decided to modernize the electronic voting application.

Principles
----------
The new version builds upon the same principles as the old version:

- One should be permitted to vote several times, overwriting previous votes
- Votes should be encrypted and stored in a different location from the rest
  of the data
- A person should only be allowed to submit one single counting vote.
  If the same person logs in with different user ID's, they should be
  linked to the same voter (using whatever ID possible).


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   install
   config
   auth
   api
   design/index
   dev/index
   audit


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
