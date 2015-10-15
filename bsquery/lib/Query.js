var underscore = require('underscore');
var async = require('async');
var bitcore = require('bitcore-multicoin');
var helper = require('./helper');
var blockstore = require('./blockstore');

var parseItemList = module.exports.parseItemList = function(req, fieldname) {
  var query = req.query;
  if(req.method == 'POST') {
    query = req.body;
  }
  var itemList = query[fieldname];
  if(!itemList) return [];
  
  return itemList.split(',');
};

var parseAddressList = module.exports.parseAddressList = function(req, fieldname) {
  fieldname = fieldname || 'addresses';
  var addressList = [];
  parseItemList(req, fieldname).forEach(function(addrStr) {
    var addr = new bitcore.Address(addrStr);
    if (addr.isValid()) {
      addressList.push(addr);
    }
  });
  return addressList;
};

var segmentAddresses = module.exports.segmentAddresses = function(addressList) {
  var segs = {};
  addressList.forEach(function(addr) {
    addr.possibleNetworks().forEach(function(network) {
      var netname = network.name;
      var s = segs[netname];
      if(s) {
	      s.arr.push(addr.toString());
      } else {
	      segs[netname] = {
	        netname: netname,
	        arr: [addr.toString()],
	      }
      }
    });
  });
  return segs;
};

module.exports.getUnspent = function(addressList, callback) {
  var segs = segmentAddresses(addressList);
  var outputs = [];
  async.forEachOf(segs, function(s, netname, cb) {
      var rpcClient = blockstore[netname];
      rpcClient.getUnspent(s.arr, function(err, arr) {
        if(err) return cb(err);
	      outputs = outputs.concat(arr.map(function(utxo) {
	        var q = utxo.toJSON();
	        q.network = netname;
	        return q;
        }));
	      return cb();
      });
  }, function(err) {
    return callback(err, outputs);
  });
};

module.exports.getUnspentV1 = function(addressList, callback) {
  var segs = segmentAddresses(addressList);
  var outputs = [];
  async.forEachOf(segs, function(s, netname, cb) {
      var rpcClient = blockstore[netname];
      rpcClient.getUnspentV1(s.arr, 200, function(err, arr) {
        if(err) return cb(err);
	      outputs = outputs.concat(arr.map(function(utxo) {
	        var q = utxo.toJSON();
	        q.network = netname;
	        return q;
        }));
	      return cb();
      });
  }, function(err) {
    return callback(err, outputs);
  });
};


module.exports.getTxDetails = function(netname, hashList, callback) {
  var rpcClient = blockstore[netname];
  rpcClient.getTxList(hashList, function(err, arr) {
    if(!err) {
      arr = arr.map(function(tTx) { return tTx.toJSON();});
    }
    return callback(err, arr);
  });
};

// Get TxList via ID
module.exports.getTxListSinceId = function(netname, sinceObjId, count, callback) {
  var rpcClient = blockstore[netname];
  if(sinceObjId) {
    rpcClient.getTxListSince(sinceObjId, count, function(err, arr) {
      if(!err) {
	      arr = arr.map(function(tTx) { return tTx.toJSON();});
      }
      return callback(err, arr);
    });
  } else {
    rpcClient.getTailTxList(count, function(err, arr) {
      //blockstore.thriftClient.getTailTxList(1, 20, function(err, arr) {
      if(!err) {
	      arr = arr.map(function(tTx) { return tTx.toJSON();});
      }
      return callback(err, arr);
    });
  }
};

module.exports.getAddrStatList = function(addresses, callback) {
  var segs = segmentAddresses(addresses);
  var addrStats = [];
  async.forEachOf(segs, function(s, netname, cb) {
    var rpcClient = blockstore[netname];
    rpcClient.getAddressStatList(s.arr, function(err, arr) {
      if(err) return cb(err);
      addrStats = addrStats.concat(arr.map(function(stat) {
        var obj = stat.toJSON();
        obj.network = netname;
        return obj;
      }));
      cb();
    });
  }, function(err) {
    return callback(err, addrStats);
  });
};

module.exports.getRelatedTxIdList = function(addresses, cursor, count, useDetail, callback) {
  var segs = segmentAddresses(addresses);
  var results = {};
  if(cursor) {
    cursor = new Buffer(cursor, 'hex');
  }
  async.forEachOf(segs, function(s, netname, cb) {
    var rpcClient = blockstore[netname];
    rpcClient.getRelatedAddrTxIdList(s.arr, cursor, count, function(err, arr) {
      if(err) return cb(err);
      if(!arr || arr.length == 0) return cb();

      var txids = [];
      var nCursor;

      arr.forEach(function(addrtx) {
        if(useDetail) {
          txids.push(addrtx.toJSON());
        } else {
          txids.push(addrtx.txid.toString('hex'));
        }
        nCursor = addrtx.cursor.toString('hex');
      });
      results[netname] = txids;
      results[netname + '.cursor'] = nCursor;
      cb();
    });
  }, function(err) {
    return callback(err, results);
  });
};

module.exports.getTxListOfAddresses = function(addresses, requireDetail, callback) {
  var segs = segmentAddresses(addresses);
  var results = [];
  async.forEachOf(segs, function(s, netname, cb) {
      var rpcClient = blockstore[netname];
      if(requireDetail) {
	      rpcClient.getRelatedTxList(s.arr, function(err, arr) {
          if(err) return cb(err);
	        if(arr.length > 0) {
	          arr = arr.map(function(tx){return tx.toJSON();});
	          results.push({netname: netname, txList: arr});
	        }
	        return cb();
	      });
      } else {
	      rpcClient.getRelatedTxIdList(s.arr, function(err,arr) {
          if(err) return cb(err);
	        if(arr.length > 0) {
	          arr = arr.map(function(txId) {
	            return txId.toString('hex');});
	          results.push({netname: netname, txList: arr});
	        return cb();
	        }
        });
      }
  }, function(err) {
    if(err) return callback(err);
    var txIDs = {};
    results.forEach(function(r) {
      if(r.txList.length > 0) {
	      txIDs[r.netname] = r.txList;
      }
    });
    callback(undefined, txIDs);
  });
};

var decodeRawTx = module.exports.decodeRawTx = function(netname, rawtx) {
  var parser = new bitcore.BinaryParser(rawtx);
  var tx = new bitcore.Transaction();
  tx.parse(parser);
  /*if(tx.serialize().toString('hex') !== rawtx.toString("hex")) {
    throw new helper.UserError('tx_rejected', 'Tx rejected');
  }*/
  return tx;
};

module.exports.addRawTx = function(netname, rawtx, info, callback) {
  rawtx = new Buffer(rawtx, 'hex');
  try {
    var tx = decodeRawTx(netname, rawtx);
    var tTx = new blockstore.ttypes.Tx();
    tTx.netname(netname);
    tTx.fromTxObj(tx);
  } catch(err) {
    console.error(err);
    return callback(err);
  }
  var rpcClient = blockstore[netname];

  async.series([
    function(c) {
      rpcClient.verifyTx(tTx, true, function(err, v) {
	      if(err) return c();
	      if(!v.verified) return c(new helper.UserError('tx_verify_failed', v.message));
	      c();
      });
    },
    function(c) {
      var sendTx = new blockstore.ttypes.SendTx();
      sendTx.hash = tTx.hash;
      sendTx.raw = rawtx;
      if(info.remoteAddress)
	      sendTx.remoteAddress = info.remoteAddress;
      if(info.sequence)
	      sendTx.sequence = info.sequence;
      rpcClient.sendTx(sendTx, c);
    },
    function(c) {
      rpcClient.addTxList([tTx], true, c);
    }
  ], function(err){
    if(err) return callback(err);
    callback(undefined, tTx.hash.toString('hex'));
  });
}
