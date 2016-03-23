FROM python:alpine

ADD awslogs setup.py /awslogs/

RUN cd awslogs && python setup.py install && cd ..

ENTRYPOINT ["awslogs"]

CMD ["-h"]

