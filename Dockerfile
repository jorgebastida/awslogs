FROM python:alpine

ADD . /awslogs/

RUN cd awslogs && python setup.py install && cd ..

ENTRYPOINT ["awslogs"]

CMD ["-h"]

