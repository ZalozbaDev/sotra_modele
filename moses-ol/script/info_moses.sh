#!/bin/bash
# echo test $0 $1

echo "" >$1

DATACOMM=$(grep commit /home/mt/smt/hsb-de/git.log)
TRAINDATE=$(grep Date /home/mt/smt/hsb-de/git.log)
SENTENCES=$(tail -n2 /home/mt/smt/hsb-de/train.log | head -n1 | cut -d ' ' -f1)
echo "Moses Statistical HSB / DE" >> $1
echo "${TRAINDATE/Date: /Train-Date:}" >> $1
echo "${DATACOMM:0:14}" >> $1
echo "Trained sentences: $SENTENCES" >> $1
echo "" >> $1

DATACOMM=$(grep commit /home/mt/smt/de-hsb/git.log)
TRAINDATE=$(grep Date /home/mt/smt/de-hsb/git.log)
SENTENCES=$(tail -n2 /home/mt/smt/de-hsb/train.log | head -n1 | cut -d ' ' -f1)
echo "Moses Statistical DE / HSB" >> $1
echo "${TRAINDATE/Date: /Train-Date:}" >> $1
echo "${DATACOMM:0:14}" >> $1
echo "Trained sentences: $SENTENCES" >> $1
echo "" >> $1

echo "" >>$1

# echo ls: `ls -l` >> $1
