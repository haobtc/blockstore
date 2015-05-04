explorer
==========
Nodejs client for blockstore thrift interface

Install
==========

```
% cd <path/to/explorer>
% npm install
```

Run servers
=======

Start a node server, node server is a p2p node which synchronize blocks from the coins' blockchain.
```
% node start.js -s node
```

Start a node server at different port and only for dogecoin and bitcoin
```
% node start.js -s node -c dogecoin -c bitcoin -p 8335
```

Start a query server 
```
% node start.js
```

Install Services
===========
```
cd <path/to/blockstore/bs-nodejs>
mkdir -p service/logs
sudo ln -s $PWD/service/blockstore.mnode /etc/service/blockstore.mnode
sudo ln -s $PWD/service/blockstore.query /etc/service/blockstore.query

```
