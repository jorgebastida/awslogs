awslogs
=======

.. image:: https://badge.fury.io/py/awslogs.png
    :target: http://badge.fury.io/py/awslogs

.. image:: https://pypip.in/d/awslogs/badge.png
    :target: https://crate.io/packages/awslogs/


awslogs is a simple command line tool to query `Amazon CloudWatch <http://aws.amazon.com/cloudwatch/>`_ logs::

    $ awslogs get /var/log/syslog *

* The latest documentation is available at: http://awslogs.readthedocs.org
* Installation instructions: http://awslogs.readthedocs.org/en/latest/installation.html

Features
--------

* Aggregate logs from accross streams and groups.

  - Aggregate all streams in a group.
  - Aggregate streams matching a regular expression.
  - Filter both groups and streams using regular expressions.

* Colored output.
* List existing groups ``awslogs groups``.
* List existing streams ``awslogs /var/log/syslog streams``.
* Watch logs as they are created ``--watch``.
* Human-friendly time filtering:

  - ``--start='23/1/2015 14:23'``
  - ``--start='2h ago'``
  - ``--start='2d ago'``
  - ``--start='2w ago'``
  - ``--start='2d ago' --end='1h ago'``

Example
-------

tbc

Contribute
-----------

* Fork the repository on GitHub.
* Write a test which shows that the bug was fixed or that the feature works as expected.

  - Use ``python setup.py test``

* Send a pull request and bug the maintainer until it gets merged and published. :) Make sure to add yourself to AUTHORS.


Helpful Links
-------------

* http://aws.amazon.com/cloudwatch/
* http://boto.readthedocs.org/en/latest/ref/logs.html
