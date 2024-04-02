FROM python:3.12
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
RUN apt-get update
RUN apt-get install -y build-essential python3-dev
RUN mkdir -p /usr/src
WORKDIR /usr/src
COPY requirements.txt /usr/src/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . /usr/src
RUN python setup.py develop
