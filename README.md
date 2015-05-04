blockstore
==========
block storage using tokumx which provides thrift interface

install
==========

```
% . setup-env.sh
% project-install
% thrift -r --gen py --gen js:node blockstore.thrift 

```

run
==========
```
% . setup-env.sh
% bin/blockstored.py
```

Install Services
===========
```
cd <path/to/blockstore>
mkdir -p service/logs
if [ ! -f /usr/local/bin/watch-service ]; then
   sudo ln -s $PWD/service/bin/watch-service /usr/local/bin/watch-service
fi

if [ ! -f /usr/local/bin/run-service ]; then
   sudo ln -s $PWD/service/bin/run-service /usr/local/bin/run-service
fi

sudo ln -s $PWD/service/blockstore.tserver /etc/service/blockstore.tserver

```
