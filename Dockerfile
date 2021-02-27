FROM debian:10

LABEL maintainer="dmintz"
RUN apt-get update
RUN apt-get install -y python3 python3-dev python3-pip fetchmail postgresql uwsgi uwsgi-plugin-python3 libmariadb-dev
RUN pip3 install --upgrade pip

COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

COPY ./ /app
WORKDIR /app
RUN chmod 700 /app/download.fetchmailrc

EXPOSE 80

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh
RUN ln -s usr/local/bin/docker-entrypoint.sh / # backwards compat
ENTRYPOINT ["docker-entrypoint.sh"]

CMD [ "uwsgi", "--ini", "/app/silverstrike.ini"]