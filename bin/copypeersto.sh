#!/bin/bash

netname=$1
tohost=$2

DATABASE="blockstore_$netname"

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


mkdir -p dump_peers
rm -rf dump_peers/*

mongodump --host $MONGODB_HOST -d $DATABASE -c peerpool -out dump_peers

check_exit

rsync -avz --progress dump_peers $tohost:~/blockstore/

check_exit

ssh $tohost "cd ~/blockstore && mongorestore --host $REMOTE_MONGODB_HOST -d $DATABASE --drop dump_peers/$DATABASE"
