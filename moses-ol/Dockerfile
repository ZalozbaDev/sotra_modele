FROM ubuntu:18.04

RUN mkdir /home/mt && mkdir /home/mt/tmp
WORKDIR /home/mt

ENV PACKAGES="wget"

RUN apt-get update && apt-get install -q -y ${PACKAGES}

RUN wget https://www.statmt.org/moses-release/RELEASE-4.0/binaries/ubuntu-17.04.tgz

RUN tar zxvf ubuntu-17.04.tgz \
&& mkdir mosesdecoder \
&& mv ubuntu-17.04/moses/bin mosesdecoder \
&& mv ubuntu-17.04/moses/scripts mosesdecoder \
&& mkdir mosesdecoder/tools \
&& mv ubuntu-17.04/training-tools/* mosesdecoder/tools

# now installing the python webservice
RUN apt-get install python3.6 -y && apt-get install python3-pip -y && apt-get install libpq-dev -y
RUN pip3 install flask
#RUN pip3 install -U flask_cors

# now do the sotra specific stuff ...
COPY model /home/mt/smt

COPY nonbreaking_prefixes  /home/mt/mosesdecoder/scripts/share/nonbreaking_prefixes
COPY script/split-sentences.perl  /home/mt/mosesdecoder/scripts/ems/support

# helper scripts for running the webservice for sotra
COPY script /home/mt/script
RUN chmod +x /home/mt/script/*
ENV MT_SCRIPTS=/home/mt/script

CMD ["/bin/bash", "-c", "LANG=C PYTHONIOENCODING=UTF-8 python3.6 script/smt-ws.py"]
