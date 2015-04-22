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
% bin/blockstored
```