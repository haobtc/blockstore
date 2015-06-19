'use strict';

var express = require('express');

var cluster = require('cluster');
var http = require('http');
var bitcore = require('bitcore-multicoin');
var config = require('./config');
var async = require('async');
var app = express();
var bodyParser = require('body-parser');
var Query = require('./Query');

var blockstore = require('./blockstore');
var helper = require('./helper');

var sendJSONP = helper.sendJSONP;

var URL_PREFIX = '/queryapi/v1';

module.exports.installAPI = function(app) {
  // Get Block by tip/height/hash
  app.get(URL_PREFIX + '/block/:netname/:blk', function(req, res, next) {
    var blk = req.params.blk;
    var rpcClient = blockstore[req.params.netname];
    function returnBlock(err, block) {
      if(err instanceof blockstore.ttypes.NotFound) {
        err = null;
      }
      if(block) {
        block.netname(req.params.netname);
        return sendJSONP(req, res, block.toJSON());
      } else {
        res.status(404).send({error: 'not found'});
      }
    }

    if(blk == 'tip') {
      return rpcClient.getTipBlock(returnBlock);
    } else if(/^[0-9A-Fa-f]{64}$/.test(blk)) {
      return rpcClient.getBlock(new Buffer(blk, 'hex'), returnBlock);
    } else if(/^\d+$/.test(blk)) {
      return rpcClient.getBlockAtHeight(parseInt(blk), returnBlock);
    } else {
      return returnBlock(undefined, null);
    }
  });

  // Get TxDetails
  function getTxDetails(req, res) {
    var query = req.query;
    if(req.method == 'POST') {
      query = req.body;
    }
    var results = [];
    function getTx(netname) {
      return function(c) {
        if(!query[netname]) {
          return c();
        }
        var hashList = query[netname].split(',');
        if(hashList.length == 0) return c();
        hashList = hashList.map(function(hash) {return new Buffer(hash, 'hex');});
        var startTime = new Date();
        Query.getTxDetails(netname, hashList, function(err, txes) {
	        if(err) return c(err);
	        //console.info('getTxDetails', netname, 'takes', (new Date() - startTime)/1000.0, 'secs');
	        results = results.concat(txes||[]);
	        c();
        });
      };
    }
    var tasks = helper.netnames().map(function(netname) {
      return getTx(netname);
    });

    if(tasks.length > 0) {
      async.parallel(tasks, function(err) {
        if(err) throw err;
        sendJSONP(req, res, results);
      });
    } else {
      sendJSONP(req, res, []);
    }
  };
  app.get(URL_PREFIX + '/tx/details', getTxDetails);
  app.post(URL_PREFIX + '/tx/details', getTxDetails);

  function getTxDetailsSinceID(req, res) {
    var query = req.query;
    if(req.method == 'POST') {
      query = req.body;
    }

    var txlist = [];

    function txTask(netname) {
      return function(c) {
        var since = query.since;
        if(since) {
	        since = new Buffer(since, 'hex');
        }
        Query.getTxListSinceId(netname, since, function(err, arr) {
	        if(err) throw err;
	        (arr||[]).forEach(function(tx) {
	          txlist.push(tx);
	        });
	        c();
        });
      };
    }

    var tasks = helper.netnames().map(function(netname) {
      return txTask(netname);
    });
    if(tasks.length > 0) {
      async.parallel(tasks, function(err) {
        if(err) throw err;
        sendJSONP(req, res, txlist);
      });
    } else {
      sendJSONP(req, res, []);
    }
  }
  // These APIs are depricated, using /queryapi/v1/tx/:netname/timeline instead
  app.get(URL_PREFIX + '/tx/since', getTxDetailsSinceID);
  app.post(URL_PREFIX + '/tx/since', getTxDetailsSinceID);

  function getTxTimelineForNetwork(req, res) {
    var netname = req.params.netname;
    var since = req.query.since;
    var startTime = new Date();
    var count = parseInt(req.query.count);
    if(isNaN(count) || count > 20 || count <= 0) {
      count = 20;
    }
    Query.getTxListSinceId(netname, since, count, function(err, arr) {
      if(err) throw err;
      var txlist = arr || [];
      //console.info('get timeline', req.params.netname, 'takes', (new Date() - startTime)/1000.0, 'secs');
      sendJSONP(req, res, txlist);
    });
  }
  app.get(URL_PREFIX + '/tx/:netname/timeline', getTxTimelineForNetwork);
  app.get(URL_PREFIX + '/tx/:netname/since', getTxTimelineForNetwork);  // For backward compitable

  app.get(URL_PREFIX + '/mempool/:netname/since', function(req, res) {
    res.send([]);
  });

  // Get unspent
  function getUnspent(req, res) {
    var query = req.query;
    if(req.method == 'POST') {
      query = req.body;
    }
    if(!query.addresses) {
      return sendJSONP(req, res, []);
    }

    var addressList = [];
    query.addresses.split(',').forEach(function(addrStr) {
      var addr = new bitcore.Address(addrStr);
      if(addr.isValid()) {
        addressList.push(addr);
      }
    });
    if(addressList.length == 0) {
      return sendJSONP(req, res, []);
    }
    var startTime = new Date();
    Query.getUnspent(addressList, function(err, results) {
      if(err) throw err;
      //console.info('getUnspent takes', (new Date() - startTime)/1000.0, 'secs');
      sendJSONP(req, res, results);
    });
  }
  app.get(URL_PREFIX + '/unspent', getUnspent);
  app.post(URL_PREFIX + '/unspent', getUnspent);

  // Get unspent
  function getTxList(req, res) {
    var query = req.query;
    if(req.method == 'POST') {
      query = req.body;
    }
    if(!query.addresses) {
      return sendJSONP(req, res, []);
    }

    var addressList = [];
    query.addresses.split(',').forEach(function(addrStr) {
      var addr = new bitcore.Address(addrStr);
      if(addr.isValid()) {
        addressList.push(addr);
      }
    });
    if(addressList.length == 0) {
      return sendJSONP(req, res, []);
    }
    var startTime = new Date();
    Query.getTxListOfAddresses(addressList, query.detail == 'yes', function(err, results) {
      if(err) throw err;
      sendJSONP(req, res, results);
    });
  }
  app.get(URL_PREFIX + '/tx/list', getTxList);
  app.post(URL_PREFIX + '/tx/list', getTxList);

  function sendTx(req, res, next) {
    var query = req.query;
    if(req.method == 'POST') {
      query = req.body;
    }
    var info = {};
    if(query.remote_address) {
      info.remoteAddress = query.remote_address;
    } else {
      info.remoteAddress = req.remoteAddress;
    }
    info.sequence = query.sequence;
    if(query.note) {
      info.note = query.note;
    }
    Query.addRawTx(req.params.netname, query.rawtx, info, function(err, ret) {
      if(err) {
        console.error('send raw tx failed', query.rawtx);
        return next(err);
      }

      if(ret != undefined) {
        if(req.query.format == 'json') {
	        sendJSONP(req, res, {'txid': ret});
        } else {
	        res.send(ret);
        }
      } else {
        res.status(400).send({'error': 'Failed'});
      }
    });
  }

  app.get(URL_PREFIX + '/sendtx/:netname', sendTx);
  app.post(URL_PREFIX + '/sendtx/:netname', sendTx);

  function decodeRawTx(req, res, next) {
    var query = req.query;
    if(req.method == 'POST') {
      query = req.body;
    }
    var tx = Query.decodeRawTx(req.params.netname, query.rawtx);
    var tTx = new blockstore.ttypes.Tx();
    tTx.netname(req.params.netname);
    tTx.fromTxObj(tx);
    sendJSONP(req, res, tTx.toJSON());
  };

  app.get(URL_PREFIX + '/decoderawtx/:netname', decodeRawTx);
  app.post(URL_PREFIX + '/decoderawtx/:netname', decodeRawTx);

  app.get(URL_PREFIX + '/:netname/nodes.txt', function(req, res) {
    var rpcClient = blockstore[req.params.netname];
    rpcClient.getPeers(function(err, peers) {
      res.set('Content-Type', 'text/plain');
      res.send(peers.join('\r\n'));
    });
  });

  app.get(URL_PREFIX + '/:netname/nodes.json', function(req, res) {
    var rpcClient = blockstore[req.params.netname];
    rpcClient.getPeers(function(err, peers) {
      res.send(peers);
    });
  });

  app.post(URL_PREFIX + '/watch/:netname/:group/addresses/', function(req, res) {
    var addresses = req.body.addresses.split(',');
    var rpcClient = blockstore[req.params.netname];
    rpcClient.watchAddresses(req.params.group, addresses, function(err, result) {
      console.info('return of watch addresses', err, res);
      sendJSONP(req, res, {"result": "ok"});
    });
  });

  app.get(URL_PREFIX + '/watch/:netname/:group/tx/list/', function(req, res) {
    var cursor = new Buffer(req.query.cursor || '', 'hex');
    var count = parseInt(req.query.count);
    if(isNaN(count) || count <= 0 || count > 50) {
      count = 50;
    }
    var rpcClient = blockstore[req.params.netname];
    rpcClient.getWatchingList(req.params.group, count, cursor, function(err, result) {
      var r = {};
      if(result.cursor) {
        r[req.params.netname + '.cursor'] = result.cursor.toString('hex');
      }
      r[req.params.netname] = result.txids.map(function(txid) {
        return txid.toString('hex');
      });
      sendJSONP(req, res, r);
    });
  });
};
