#!/bin/bash

netname=$1
tohost=$2
count=$3

height=`ssh $tohost "cd blockstore && source setup-env.sh && python bin/get_tip_height.py $netname"`

echo remote tip height is $height

function check_exit() {
    if [ $? -ne 0 ]; then
        exit
    fi
}

if [ -z $MONGODB_HOST ]; then
    export MONGODB_HOST='localhost:27017'
fi

if [ -z $REMOTE_MONGODB_HOST ]; then
    export REMOTE_MONGODB_HOST='localhost:27017'
fi

start_height=`expr $height - 1`
r_count=`expr $count + 1`

python bin/dumpblocks.py $netname $start_height $r_count

check_exit

mkdir -p bdump
rm -rf bdump/*

mongodump --host $MONGODB_HOST -d blockdump -out bdump

check_exit

rsync -avz --progress bdump $tohost:~/blockstore/

check_exit

ssh $tohost "cd ~/blockstore && mongorestore --host $REMOTE_MONGODB_HOST -d blockdump --drop bdump/blockdump && source setup-env.sh  && python bin/copyblocks.py $netname $count"
