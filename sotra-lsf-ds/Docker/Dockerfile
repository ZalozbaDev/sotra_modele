FROM python:3.9.7

WORKDIR /app

RUN pip config --user set global.progress_bar off
RUN pip install Cython
RUN pip install flask
RUN pip install flask-cors
RUN pip install ctranslate2
RUN pip install sacremoses
RUN pip install sentence_splitter
RUN pip install youtokentome


COPY sentence_splitter/non_breaking_prefixes /app/sentence_splitter/non_breaking_prefixes

COPY inference_new2.py /app/

CMD ["python3", "inference_new2.py"]
