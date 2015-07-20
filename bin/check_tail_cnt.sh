#!/bin/bash

netname=$1
. setup-env.sh

tip_height=`python bin/get_tip_height.py $netname`

start_height=`expr $tip_height - 200`

python bin/check_cnt_txes.py $netname $start_height 300 | grep 'cnt mismatch' | awk '{print $3}' | tee /tmp/mismatch.txt

cnt=`wc -l /tmp/mismatch.txt|awk '{print $1}'`

echo `date` checking $start_height $cnt>/tmp/st.txt

if [ $cnt -gt 0 ]; then
    cd bsquery
    for bh in $(cat /tmp/mismatch.txt); do node start.js -s fetch -c $netname -b $bh; done
fi
