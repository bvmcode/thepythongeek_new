FROM ubuntu:20.04

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev libpq-dev unixodbc-dev libsasl2-dev\
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip 

COPY ./requirements.txt /app/
COPY ./client/ /app/

WORKDIR /app

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

CMD ["uwsgi", "app.ini"]