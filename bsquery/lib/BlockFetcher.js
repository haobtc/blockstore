var bitcore = require('bitcore-multicoin');
var underscore = require('underscore');
var async = require('async');
var util = bitcore.util;
var helper = require('./helper');
var config = require('./config');
var blockstore = require('./blockstore');

var Peer = bitcore.Peer;
var PeerManager = bitcore.PeerManager;

var Script = bitcore.Script;
var buffertools = require('buffertools');
var Skip = helper.Skip;

var hex = function(hex) {return new Buffer(hex, 'hex');};

function BlockFetcher(netname, blockHash) {
  this.netname = netname;
  this.waitingBlockHash = blockHash;

  this.peerman = new PeerManager({
    network: this.netname
  });
  this.peerman.peerDiscovery = true;
}

BlockFetcher.prototype.checkBlockHashes = function(callback) {
  var self = this;
  var rpcClient = blockstore[this.netname];
  rpcClient.getBlock(this.waitingBlockHash, function(err, b) {
    console.info('got block', b);
    if(err) {
      if(err instanceof blockstore.ttypes.NotFound) {
	b = null;
      } else{
	return callback(err);
      }
    }
    if(b && b.isMain) {
      self.waitingBlockHash = b.hash;
      return callback();
    } else {
      callback(new Error('Canot find block'));
    }
  });
};

BlockFetcher.prototype.run = function(callback) {
  var self = this;
  var rpcClient = blockstore[this.netname];
  console.info('rpcClient', rpcClient);
  rpcClient.getPeers(function(err, v) {
    console.info('got peers', err, v);
    if(err) return callback(err);
    var peers = config.networks[self.netname].peers;
    if(v && v.peers && v.peers.length > 0) {
      peers = v.peers;
    }

    var p2pPort = bitcore.networks[self.netname].defaultClientPort;
    peers.forEach(function(peerHost){
      if(peerHost.indexOf(':') < 0) {
	peerHost = peerHost + ':' + p2pPort;
      }
      self.peerman.addPeer(new Peer(peerHost));
    });

    self.peerman.on('connection', function(conn) {
      conn.on('inv', self.handleInv.bind(self));
      conn.on('block', self.handleBlock.bind(self));
    });

    self.peerman.on('netConnected', function(info) {
      if(typeof callback == 'function') {
	callback();
      }
      setInterval(function() {
        self.fetchBlock();
      }, 3000);
    });
    self.peerman.start();
    callback();
  });
};

BlockFetcher.prototype.stop = function(cb) {
  this.blockChain.stop(cb);
};

BlockFetcher.prototype.handleBlock = function(info) {
  var block = info.message.block;
  var bHash = block.calcHash(bitcore.networks[self.netname()].blockHashFunc);
  bHash = helper.reverseBuffer(bHash);
  console.info('bb', bHash);
  if(bHash.toString() == this.watingBlockHash.toString()) {
    this.onBlock(block, {rawMode: false}, function(err, q) {
      if(err) throw err;
    });
  }
};

BlockFetcher.prototype.handleRawBlock = function(info) {
  var self = this;
  this.stopOnTimeout();
   var block = new bitcore.Block();
  block.parse(info.message.parser, true);
  var bHash = block.calcHash(bitcore.networks[this.netname].blockHashFunc);
  bHash = helper.reverseBuffer(bHash);
  console.info('bb', bHash);
  if(bHash.toString() == this.watingBlockHash.toString()) {
    this.onBlock(block, {rawMode: true}, function(err, q) {
      if(err) throw err;
    });
  }
};


BlockFetcher.prototype.fetchBlock = function() {
  var self = this;
  var invs = [{
    'type': 2,
    'hash': helper.reverseBuffer(this.waitingBlockHash)
  }];

  console.info('fetch block', invs);

  var conns = this.randomConns();
  if(!conns || conns.length == 0) {
    console.warn(this.netname, 'No active connections');
    return;
  }

  conns.forEach(function(conn) {
    console.info(self.netname, 'getting invs', invs, 'from', conn.peer.host);
    conn.sendGetData(invs);
  });
};

BlockFetcher.prototype.randomConns = function(n) {
  var activeConnections = this.peerman.getActiveConnections();
  if(activeConnections.length == 0) {
    console.warn(this.netname, 'No active connections');
    return;
  }
  var len = activeConnections.length;
  var indexes = [];
  for(var i=0; i<n; i++) {
    var idx = Math.floor(Math.random() * len);
    indexes.push(idx);
  }
  indexes = underscore.uniq(indexes);
  var conns = indexes.map(function(idx) {
    return activeConnections[idx];
  });
  console.info('dddd', conns);
  return conns;
};

BlockFetcher.prototype.handleInv = function(info) {
  var invs = info.message.invs;
  info.conn.sendGetData(invs);
};

BlockFetcher.prototype.onBlock = function(block, opts, callback) {
  var self = this;
  var txIdList = [];
  var newTxIdList;
  var blockVerified;
  var tBlock = new blockstore.ttypes.Block();
  tBlock.netname(this.netname);
  tBlock.fromBlockObj(block);

  var rpcClient = blockstore[this.netname];

  if(opts.rawMode) block.parseTxes(opts.parser);
  tBlock.cntTxes = block.txs.length;
  var txList = block.txs.map(function(tx) {
    var tTx = new blockstore.ttypes.Tx();
    tTx.netname(self.netname);
    tTx.fromTxObj(tx);
    txIdList.push(tTx.hash);
    return tTx;
  });
  
  async.series(
    [
      function(c) {
	if(txIdList.length ==0) return c();
	rpcClient.getMissingTxIdList(txIdList, function(err, arr) {
	  if(err) return c(err);
	  newTxIdList = arr;
	  c();
	});
      },
      function(c) {
	if(!newTxIdList || newTxIdList.length == 0) return c();
	var newTxIdMap = {};
	newTxIdList.forEach(function(txId) {
	  newTxIdMap[txId.toString('hex')] = true;
	});

	var newTxList = txList.filter(function(tTx) {
	  return !!newTxIdMap[tTx.hash.toString('hex')];
	});
	if(newTxList.length == 0) return c();
	rpcClient.addTxList(newTxList, false, c);
      },
      function(c) {
	rpcClient.linkBlock(tBlock.hash, txIdList, c);
      }
    ],
    callback);
};

BlockFetcher.prototype.start = function(callback) {
  var self = this;
  async.series([
    function(c) {
      return self.checkBlockHashes(c);
    },
    function(c) {
      return self.run(c);
    },
  ], callback);
};

module.exports = BlockFetcher;
