#!/bin/bash

echo "Translate file $1"
echo "================="

# example:
# ./0020_run_streaming_translate.sh ~/speech_corpus_internal_kamishibai_sst_2021/rohdaten/2021-04-SST-01-Cerwjenawka.txt

python3 streaming_translate.py $1
