FROM python:2
MAINTAINER Ivan Pedrazas <ipedrazas@gmail.com>

RUN pip install awslogs

# We need to install gevent from git because of a bug
# https://github.com/docker-library/python/issues/29
RUN pip install --upgrade cython git+git://github.com/surfly/gevent.git#egg=gevent
