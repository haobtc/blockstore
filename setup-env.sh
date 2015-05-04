#!/bin/bash

ENVDIR=$PWD/../ENV2
export PYTHONPATH="$PWD/lib:$ENVDIR:$PYTHONPATH"
export PATH="$ENVDIR/bin:$PATH"

function project-install() {
    if [ ! -d $ENVDIR ]; then
	virtualenv $ENVDIR
    fi
    pip install -r requirements.txt
}

