=======
Testing
=======

This document provides instructions and recipes for testing the code before
submitting.

The only required procedure is as follows:

1. Make sure, you have `tox` installed::

   $ pip install -U tox

2. Run all tests across all locally available python versions::

   $ tox

Make sure, all tests are passing.

If it runs in at least one python version, you may ignore the `ERROR:
pyXY: InterpreterNotFound: pythonX.Y` errors.

.. contents:: Table of contents

Concepts
========

The testing infrastructure built on top of set of tools, explained in this
section.

`py.test` - test runner
-----------------------
Test runner collects available tests, runs some or all of them, reports
problems and even allows jumping into command line debugger if you need it.

There are multiple test runners available, here we use pytest_.

.. _pytest: http://pytest.org/latest/

`pytest` is mostly installed by running `tox` (see below), but can be installed by::

    $ pip test pytest

After that, command `py.test` shall be available.

Tests are placed in `tests` subdirectory or subdirectories.

To run all tests in `tests` subdirectory, be a bit verbose and print possible
output printed to stdout by your testing code::

    $ py.test -sv tests

To run all tests defined in `tests/test_it.py`::

    $ py.test -sv tests/test_it.py

pytest_ allows running most tests written for `unittest`, `nose` and other testing frameworks.

pytest_ also allows writing test cases using so called fixtures, which allow
writing very readable modular test suites.

Another strong point of `pytest` is error reporting. Generated reports are very well readable.

"virtualenv" - isolated environment
-----------------------------------

Virtual environments, or "virtualenv" in short is a tool, allowing to run your
python code in isolated python environment. It has the advantage, that you may
safely install into it without spoiling global python environment or being
restricted by what is installed in the global environment.

`virtualenv` can be set up by means of various tools (virtualenv_, tox_,
virtualenvwrapper_, venv_ and others).

In our case, we rely on `tox` command to create well defined virtual
environment, which can be easily recreated, extended and activated.

For that reason, there is no reason to install virtualenv separately.

.. _virtualenv: https://virtualenv.pypa.io/en/latest/

.. _tox: https://testrun.org/tox/latest/

.. _virtualenvwrapper: http://virtualenvwrapper.readthedocs.org/en/latest/

.. _venv: https://docs.python.org/3/library/venv.html


`tox` - automate testing across multiple python versions
--------------------------------------------------------

Building and testing python code might be complex as it involves building
fresh version of tested package, installing it incl. dependencies, installing
packages needed for testing, running test. This all is often needed in multiple
python versions and preferably shall be done using virtual environments.

With tox_, you just jump into directory with `tox.ini` and run::

    $ tox

`coverage` - see what code lines are ignored by tests
-----------------------------------------------------
Test coverage is checking, what lines of tested code were executed during
tests. The higher percentage the better.

The tool even allows to show checked code and highlight the lines, which were
not executed. There are often the lines, where bugs are present.

This project is using coverage_ tool.

.. _coverage: http://coverage.readthedocs.org/en/

Recipes
=======

This section provides practical instructions for specific activities related to
testing and development.

Run all tests in all python versions
------------------------------------
The command::

    $ tox

Will run all tests in all relevant python interpreters installed on your machine.

Relevant interpreters are defined in `tox.ini` file.

In case some python version is to be tested but is not installed, it reports
`ERROR: pyXY: InterpreterNotFound: pythonX.Y` error. This shall not happen for
the version you are developing, for other versions you can safely ignore this
message.

.. warning:: **`tox` shall not be started in activated virtualenv.**
    If you run `tox` in activated virtualenv, you may experience strange
    results.


Run all tests under one python version using `tox`
--------------------------------------------------
First, check, what python versions is `tox` configured to run for::

    $ tox -l
    py26
    py27
    py33
    py34

Assuming you want to run tests for python 2.7, run::

    $ tox -e py27

Creating and recreating virtualenvs by `tox`
--------------------------------------------

Running `tox`, one or more virtualenvs are always created::

    $ tox -e py27

Virtualenvs are by default located in `.tox` directory::

    $ dir .tox
    dist
    log
    py27

.. note:: Ignore the `dist` and `log` directories. There may be more directories like `py34`.

To activate virtualenv on Linux::

    $ source .tox/py27/bin/activate

On MS Windows::

    $ source .tox/py27/Scripts/activate

After you activate virtualenv, command prompt often stars showing name of the virtualenv, e.g.::

    (py27) $

This is shell specific behaviour.

You may install new packages into activated environment::

    $ pip install anotherpackage

To deactivate virtualenv::

    $ deactivate

If you need to recreate the environment, you may either remove given directory,
or ask `tox` to recreate it::

    $ tox -e py27 -r

Run all tests under one python version using `py.test`
------------------------------------------------------

First, create and activate virtualenv for your target python version (as described above).

Then run all the tests::

    $ py.test -sv tests

See `pytest` help for more options (see e.g. `--pdb` which starts command line
debugger in case some test fails).


Run selected tests under one python version using `py.test`
-----------------------------------------------------------

First, create and activate virtualenv for your target python version (as described above).

Then run the test of your interest::

    $ py.test -sv tests/test_it.py

For more methods of selecting tests see: `Specifying tests / selecting tests`_

.. _`Specifying tests / selecting tests`: https://pytest.org/latest/usage.html#specifying-tests-selecting-tests

Check test coverage
-------------------

First, create and activate virtualenv for your target python version (as described above).

To test coverage of complete package `awslogs`::

    $ coverage run --source awslogs -m pytest tests/

This creates or updates a file `.coverage`.

To show coverage report on console::

    $ coverage report
    Name                    Stmts   Miss  Cover
    -------------------------------------------
    awslogs/__init__.py         2      0   100%
    awslogs/bin.py             85      9    89%
    awslogs/core.py           143     12    92%
    awslogs/exceptions.py      12      2    83%
    -------------------------------------------
    TOTAL                     242     23    90%

You may also generate nice HTML report, showing your source code highlighting
lines, which were ignored by your tests.

First create the HTML report::

    $ coverage html

Then open it in your web browser, e.g. in Firefox::

    $ firefox htmlcov/index.html


Release a new version
---------------------

This task is relevant to package maintainer only.

When is all ready for release:

1. Commit all changes to git
2. Run the tests to be sure, all is really ready
3. Add "version" tag to git, e.g.: `$ git tag -a 9.10`
4. Build the distributable (more details below)
5. Upload the distributable to pypi as usually

To build the distributable, there are few options.

Running `tox` creates the package in `.tox/dist` directory.

Or you may activate relevant virtualenv and run::

    $ python setup.py <buld_command_you_prefer>
