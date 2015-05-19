FROM python:2


RUN pip install awscli awslogs

RUN pip install --upgrade cython git+git://github.com/surfly/gevent.git#egg=gevent

