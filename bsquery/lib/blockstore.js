var argv = require('optimist').argv;
var bitcore = require('bitcore-multicoin');
var thrift = require('thrift');
var helper = require('./helper');
var BlockStoreService = require('./gen-nodejs/BlockStoreService');
var ttypes = require('./gen-nodejs/blockstore_types');
var config = require('./config');

// Initialize 
var networkType2NameMap = {};
ttypes.Block.prototype.netname = function(netname) {
  if(!netname) {
    return networkType2NameMap[this.nettype];
  } else {
    this.nettype = ttypes.Network[netname.toUpperCase()];
  }
};

ttypes.Block.prototype.fromBlockObj = function(blockObj) {
  var self = this;
  var bHash = blockObj.calcHash(bitcore.networks[self.netname()].blockHashFunc);
  this.hash = helper.reverseBuffer(bHash);
  this.timestamp = blockObj.timestamp;
  this.version = blockObj.version;
  this.merkleRoot = blockObj.merkle_root;
  this.prevHash = helper.reverseBuffer(blockObj.prev_hash);
  if(blockObj.bits) {
    this.bits = blockObj.bits;
  }
};

ttypes.Block.prototype.toJSON = function() {
  var obj = {
    hash: this.hash.toString('hex'),
    version: this.version,
    timestamp: this.timestamp,
    merkle_root: this.merkleRoot.toString('hex'),
    height: this.height,
    prev_hash: this.prevHash.toString('hex'),
    confirmations: 0,
    tx_cnt: this.cntTxes
  };

  var rpcClient = module.exports[this.netname()];
  if(rpcClient.tipBlock) {
    obj.confirmations = Math.max(0, rpcClient.tipBlock.height - this.height + 1);
  }

  if(this.nextHash) {
    obj.next_hash = this.nextHash.toString('hex');
  }
  if(this.bits) {
    obj.bits = this.bits.toNumber();
  }
  return obj;
};

ttypes.Tx.prototype.netname = function(netname) {
  if(!netname) {
    return networkType2NameMap[this.nettype];
  } else {
    this.nettype = ttypes.Network[netname.toUpperCase()];
  }
};

ttypes.Tx.prototype.setBlock = function(block, blockIndex) {
  if(block) {
    this.block = block;
  }
  if(blockIndex >= 0) {
    this.blockIndex = blockIndex;
  }
};

ttypes.Tx.prototype.fromTxObj = function(txObj, netname) {
  var self = this;
  this.hash = helper.reverseBuffer(txObj.hash);
  this.version = txObj.version;
  this.inputs = txObj.ins.map(function(input, i) {
    var txInput = new ttypes.TxInput();
    var n = input.getOutpointIndex();
    if(n >= 0) {
      txInput.hash = helper.reverseBuffer(new Buffer(input.getOutpointHash()));
      txInput.vout = n;
    }
    txInput.script = input.s;
    txInput.q = input.q;
    // Missing address and amountSatoshi
    return txInput;
  });
  
  this.outputs = txObj.outs.map(function(out, i) {
    var txOut = new ttypes.TxOutput();
    txOut.script = out.s;
    if(out.s) {
      var script = new bitcore.Script(out.s);
      txOut.address = script.getAddrStr(self.netname()).join(',');
    }
    txOut.amountSatoshi = bitcore.util.valueToBigInt(out.v).toString();
    return txOut;
  });
};

ttypes.Tx.prototype.toJSON = function() {
  var self = this;
  var obj = {
    txid: this.hash.toString('hex'),
    confirmations: 0,
    network: this.netname()
  };
  obj.hash = obj.txid;
  if(this.objId) {
    obj.id = this.objId.toString('hex');
  }
  if(this.block) {
    obj.blockhash = this.block.hash.toString('hex');
    obj.blockheight = this.block.height;
    obj.blocktime = this.block.timestamp;
    obj.time = this.block.timestamp;
    var rpcClient = module.exports[this.netname()];
    if(rpcClient.tipBlock) {
      obj.confirmations = Math.max(0, rpcClient.tipBlock.height - this.block.height + 1);
    }
  } else {
    obj.time = Math.floor(new Date().getTime()/1000);
  }
  if(this.blockIndex != null) {
    obj.blockindex = this.blockIndex;
  }

  obj.inputs = this.inputs.map(function(input) {
    var iObj = {
      script: input.script.toString('hex'),
      amount: '0',
      amountSatoshi: '0'
    };
    if(input.hash) {
      iObj.hash = input.hash.toString('hex'),
      iObj.vout = input.vout;
    }
    if(input.address) {
      iObj.address = input.address;
    }
    if(input.amountSatoshi) {
      iObj.amount = helper.satoshiToNumberString(input.amountSatoshi);
      iObj.amountSatoshi = input.amountSatoshi;
    }
    return iObj;		
  });

  obj.outputs = this.outputs.map(function(output) {
    return {
      script: output.script.toString('hex'),
      address: output.address,
      amount: helper.satoshiToNumberString(output.amountSatoshi),
      amountSatoshi: output.amountSatoshi      
    };
  });
  return obj;
};

ttypes.UTXO.prototype.netname = function(netname) {
  if(!netname) {
    return networkType2NameMap[this.nettype];
  } else {
    this.nettype = ttypes.Network[netname.toUpperCase()];
  }
};

ttypes.UTXO.prototype.toJSON = function() {
  var obj = {
    network: this.netname(),
    address: this.address,
    txid: this.txid.toString('hex'),
    amountSatoshi: this.amountSatoshi,
    amount: helper.satoshiToNumberString(this.amountSatoshi),
    vout: this.vout,
    scriptPubKey: this.scriptPubKey.toString('hex'),
    timestamp: this.timestamp,
    confirmations: this.confirmations
  };
  return obj;
};

ttypes.Peer.prototype.fromPeer = function(p) {
  this.host = p.host;
  this.port = p.port;
  this.time = p.lastSeen;
  this.services = p.services;
};

ttypes.Peer.prototype.toPeer = function(p) {
  var p = new bitcore.Peer(this.host, this.port); // services
  p.lastSeen = this.time;
  return p;
};

transport = thrift.TBufferedTransport()
protocol = thrift.TBinaryProtocol()

function tServerConfigList() {
  function parseTServerString(s) {
    var t = s.split(':', 2);
    if(t.length < 2)
      throw new Error('Illegal tserver string ' + s);
    var host = t[0];
    var port = parseInt(t[1]);
    if(isNaN(port))
      throw new Error('Illegal port ' + s);
    return {host: host, port: port};
  }

  var srvs = [];

  if(srvs.length == 0) {
    if(argv.tserver instanceof Array) {
      srvs = argv.tserver.map(parseTServerString);
    } else if(argv.tserver) {
      srvs = [parseTServerString(argv.tserver)];
    }
  }
  
  if(srvs.length == 0) {
    var tserver = process.env.BLOCKSTORE_TSERVER;
    if(tserver) {
      srvs = tserver.split(';').map(parseTServerString);
    }
  }

  if(srvs.length == 0) {
    srvs = config.blockstore;
    if(!(srvs instanceof Array)) {
      srvs = [srvs];
    }
  }

  if(srvs.length == 0) {
    throw new Error('No tserver found');
  }
  return srvs;
}

function makeConnection() {
  var tServers = tServerConfigList();
  //console.info('tservers', tServers);
  var tServerConfig = tServers[Math.floor(Math.random() * tServers.length)];

  var connection = thrift.createConnection(tServerConfig.host,
					   tServerConfig.port, {
    transport : transport,
    protocol : protocol,
    max_attempts: 1000000
  });

  connection.on('error', function(err) {
    console.error('thrift error', err);
  });
  return connection;
}

module.exports.ttypes = ttypes;

var thriftClient = module.exports.thriftClient = thrift.createClient(BlockStoreService, makeConnection());

/* RPC wrapper */
function RPCWrapper(netname) {
  var self = this;
  this.netname = netname;
  this.networkType = ttypes.Network[netname.toUpperCase()];
  this.tipBlock = null;
}

RPCWrapper.prototype.keepTip = function() {
  var self = this;
  function getTip() {
    self.getTipBlock(function(err, block) {
      if(err instanceof ttypes.NotFound) {
	err = null;
      }
      if(err) {
	throw err;
      }
      if(block) {
	self.tipBlock = block;
      }
    });
  }
  setInterval(getTip, 5000);
  getTip();
};

['getBlock', 'getBlockAtHeight', 'getTipBlock', 'verifyBlock', 'addBlock', 'getTailBlockList', 'linkBlock',
 'getTx', 'getTxList', 'getMissingTxIdList', 'verifyTx', 'addTxList', 'removeTx',
 'getTxListSince', 'getTailTxList', 'getRelatedTxList', 'getRelatedTxIdList',
 'getSendingTxList', 'getSendTxList', 'sendTx', 'getUnspent', 'getMissingInvList',
 'setPeers', 'getPeers', 'pushPeers', 'popPeers',
 'watchAddresses', 'getWatchingList'
].forEach(function wrapRpc(clientRpc) {
  RPCWrapper.prototype[clientRpc] = function() {
    var args = [];
    args.push(this.networkType);
    for(var i=0; i<arguments.length; i++) {
      args.push(arguments[i]);
    }
    return thriftClient[clientRpc].apply(thriftClient, args);
  };
});

helper.netnames().forEach(function(netname) {
  networkType2NameMap[ttypes.Network[netname.toUpperCase()]] = netname;
  module.exports[netname] = new RPCWrapper(netname);
});

module.exports.keepTip = function() {
  helper.netnames().forEach(function(netname) {
    var rpcClient = module.exports[netname];
    if(rpcClient) {
      setTimeout(rpcClient.keepTip.bind(rpcClient), Math.random() * 2000);
    }
  });
}
