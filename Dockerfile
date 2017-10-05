FROM ubuntu:16.04

# Install dependencies
RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install build-essential libevent-dev libssl-dev
RUN apt-get -y install git
RUN apt-get -y install python python3 python3-dev python-pip python-virtualenv

# Setup illume
RUN mkdir -p /app/illume
COPY Modules /app/illume/Modules/
COPY docs /app/illume/docs/
COPY illume /app/illume/illume/
COPY tests /app/illume/tests/
COPY makedeps.sh setup.py .coveagerc /app/illume/
WORKDIR "/app/illume"
RUN virtualenv -p `which python3` env
RUN . env/bin/activate && python setup.py install
RUN . env/bin/activate && python setup.py test
