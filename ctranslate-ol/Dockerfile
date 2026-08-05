FROM python:3.9

WORKDIR /app

RUN pip config --user set global.progress_bar off
RUN pip install Cython
RUN pip install flask
RUN pip install flask-cors
RUN pip install waitress
RUN pip install urlextract
RUN pip install opus-fast-mosestokenizer
RUN pip install ctranslate2
RUN pip install youtokentome
RUN pip install ruamel.yaml

COPY nonbreaking_prefixes/nonbreaking_prefix.* /usr/local/lib/python3.9/site-packages/mosestokenizer/share/nonbreaking_prefixes/
COPY nonbreaking_prefixes/protected_pattern /usr/local/lib/python3.9/site-packages/mosestokenizer/share

RUN useradd -u 1000 -m ctranslate

COPY --chown=1000:1000 CTranslator.py /app/
COPY --chown=1000:1000 version.txt    /app/
COPY --chown=1000:1000 models         /app/models

USER 1000

#COPY CTranslator.py /app/
#COPY version.txt    /app/
#COPY models /app/models

CMD ["python", "CTranslator.py"]
