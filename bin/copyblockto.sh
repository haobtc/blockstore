#!/bin/bash

netname=$1
tohost=$2
height=$3
count=$4

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

start_height=`expr $height - 2`
r_count=`expr $count + 2`

python bin/dumpblocks.py $netname $start_height $r_count

check_exit

mkdir -p bdump
rm -rf bdump/*

mongodump --host $MONGODB_HOST -d blockdump -out bdump

check_exit

rsync -avz bdump $tohost:~/blockstore/

check_exit

ssh $tohost "cd ~/blockstore && mongorestore --host $REMOTE_MONGODB_HOST -d blockdump --drop bdump/blockdump"

