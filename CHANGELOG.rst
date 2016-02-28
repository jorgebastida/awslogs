0.4.0
=====
* Fix utf-8 issues

0.3.0
=====
* Add ``--timestamp`` and ``--ingestion-time`` Thanks vlcinsky #36
* Fix help texts. Thanks Daniel Hahler #46
* Add flake8 to travis

0.2.0
=====
* Add ``--filter-pattern`` option. #28
* Fix issue with --end default value in  Windows 10 x64. #24
* Added support for ``--profile`` #29
* Fix argparse error in Python 3. #31
* Fix some filtering stream issues #32
* Default value for ``--start`` is now 5 minutes instead of 24h.

0.1.2
=====
* Add some documentation about installing awslogs in "El Capitan"
* Fix #21 - Problems to stop awslogs when pressing Ctrl+C.

0.1.1
=====
* Fix dependecies so installing awslogs from pypi works again.

0.1.0
=====
* awslogs now use ``boto3`` instead of ``boto2``.
* awslogs don't longer require ``gevent``.
* massive refactoring of the internals now that ``aws`` provides ``filter_log_events`` out the box.
* awslogs don't longer support retrieving logs from several groups at the same time.
* awslogs now support python: 2.7, 3.3 and 3.4

0.0.3
=====
* Filter streams by ``start`` and ``end`` in order to reduce the initial volume of queries #9.
* Fix next_token unbound after exception #8

0.0.2
=====
* Deal with AccessDeniedException properly #3.
* Return some helpful information if boto raises NoAuthHandlerFound #2.
* Make --aws-access-key-id, --aws-secret-access-key and --aws-region available to all parsers (groups, streams, get).
* Make it required to provide a valid region using --aws-region or AWS_REGION.
* Improve error messages by providing some hints.
* Add MANIFEST file #7.

0.0.1
=====
* Initial release
