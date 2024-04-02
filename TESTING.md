# Testing

This document provides instructions and recipes for testing the code
before submitting.

The only required procedure is as follows:

1.  Make sure, you have `tox` installed::

    $ pip install -U tox

2.  Run all tests across all locally available python versions::

    $ tox

Make sure, all tests are passing.

If it runs in at least one python version, you may ignore the
`ERROR: pyXY: InterpreterNotFound: pythonX.Y` errors.

## Release a new version

This task is relevant to package maintainer only.

When is all ready for release:

1.  Commit all changes to git
2.  Run the tests to be sure, all is really ready
3.  Add “version” tag to git, e.g.: `$ git tag -a 9.10`
4.  Build the distributable (more details below)
5.  Upload the distributable to pypi as usually

To build the distributable, there are few options.

Running `tox` creates the package in `.tox/dist` directory.

Or you may activate relevant virtualenv and run::

    $ python setup.py <buld_command_you_prefer>
