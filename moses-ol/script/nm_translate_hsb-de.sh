#!/bin/bash
# echo test $0 $1 $2

# gdown https://drive.google.com/uc?id=1n9N7Vmq8PJlMZw0Kx5a29r8VQ9sGkhNl
# /uc?id= muss eingef�gt werden

cd /home/mt/nmt

cat $1 | \
	~/mosesdecoder/scripts/tokenizer/normalize-punctuation.perl -l hsb | \
	${MT_PATH}/data/extcmd/preproc_splitsentences.pl | \
	~/mosesdecoder/scripts/ems/support/split-sentences.perl -q -l hsb -n -k | \
	~/mosesdecoder/scripts/tokenizer/tokenizer.perl -q -a -no-escape -l hsb | \
	sed -E 's/\b([[:alpha:]]+?) @\-@ li\b/\1-li/g' | \
	~/mosesdecoder/scripts/recaser/truecase.perl --model ~/smt/hsb-de/truecase-model.hsb > $3

	# onmt_translate -model hsb-de_step_100000.pt -src $2 -output $3 -phrase_table phrase_table.txt -batch_type tokens -verbose 1>&2
	onmt_translate -model hsb-de_step_100000.pt -fp32 -src $3 -output $4 -replace_unk

	cat $4 | ~/mosesdecoder/scripts/tokenizer/detokenizer.perl -a -q | sed -E 's/^[[:punct:]]*[[:alpha:]]/\U&/; s/<unk>/ <unk>/gi' > $2

#echo Dies ist ein Test f�r die Ausgabe nach stderr 1>&2
