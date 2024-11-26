#!/bin/bash
#echo ______ sm_translate_de.sh $0 $1 $2 $3 $4 $5 $6 $7 >>~/tmp.txt

SRC_LANG=$1
DST_LANG=$2

FILE_SRC=$3
FILE_SRC_SENTENCE_OUTPUT=$4
FILE_SRC_MOSES=$5
FILE_DST_TRANSLATION_RAW=$6
FILE_DST_SENTENCE_RESULT=$7

cat $FILE_SRC | sed 's/\r$//' | \
${MT_SCRIPTS}/main_splitsentences.pl in $SRC_LANG $FILE_SRC_SENTENCE_OUTPUT | \
./mosesdecoder/scripts/tokenizer/normalize-punctuation.perl -l $SRC_LANG | \
./mosesdecoder/scripts/tokenizer/tokenizer.perl -q -a -no-escape -l $SRC_LANG | \
sed -E 's|\b([[:alpha:]]+?) @\-@ li\b|\1-li|g' | \
./mosesdecoder/scripts/recaser/truecase.perl --model ./smt/$SRC_LANG-$DST_LANG/truecase-model.$SRC_LANG | \
${MT_SCRIPTS}/ph_nes.pl | \
./mosesdecoder/scripts/generic/ph_numbers.perl | tee $FILE_SRC_MOSES | \

./mosesdecoder/bin/moses -f ./smt/$SRC_LANG-$DST_LANG/moses.ini \
	--mark-unknown \
	--unknown-word-prefix '<unk>' \
	--unknown-word-suffix '</unk>' \
	-placeholder-factor 1 \
	-xml-input exclusive | \

./mosesdecoder/scripts/tokenizer/detokenizer.perl -a -q | sed -E 's/^[[:punct:]]*[[:alpha:]]/\U&/; s/<unk>/ <unk>/gi' >$FILE_DST_TRANSLATION_RAW
cat $FILE_DST_TRANSLATION_RAW | ${MT_SCRIPTS}/main_splitsentences.pl out $SRC_LANG $FILE_SRC_SENTENCE_OUTPUT $FILE_DST_SENTENCE_RESULT
