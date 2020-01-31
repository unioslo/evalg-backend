Design
======

.. toctree::
   :maxdepth: 2

   election-types
   voters-review-before-counting
   ballot-encryption

.. todo::

   Write about the main design principles


Hovedprinsipper og designvalg
-----------------------------


Skille institusjoner
....................

Evalg 2 hadde støtte for flere institusjoner i samme instans.
I eValg 3 har vi valg å gå bort fra dette.

Det er kun mulig å ha en institusjoner per instans.
Hver instans kjørers som egne containere med egne database.
