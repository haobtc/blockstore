blockstore
==========
block storage using tokumx which provides thrift interface

install
==========

```
% . setup-env.sh
% project-install
```

run blockstored
==========
```
% . setup-env.sh
% bin/blockstored
```

Optional: generate thrift libraries
==========
```
thrift -r --gen py -out lib etc/blockstore.thrift 
thrift -r --gen js:node -o bsquery/lib etc/blockstore.thrift 

```

```

Optional: Install supervisor services
===========
```
% cd <path/to/blockstore>
% cd etc/supervisor
% cp blockstore.example.conf blockstore.conf  

edit blockstore.conf to fit your settings
% cd ../..
% sudo ln -s $PWD/etc/supervisor/blockstore.conf /etc/supervisor/conf.d/blockstore.conf

```
