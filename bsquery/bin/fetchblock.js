var express = require('express');
var bodyParser = require('body-parser');
var bitcore = require('bitcore-multicoin');
var NodeSet = require('../lib/NodeSet');
var helper = require('../lib/helper');
var config = require('../lib/config');

var nodeSet = new NodeSet();

module.exports.start = function(argv){
  var coins = argv.c;
  if(typeof coins == 'string') {
    coins = [coins];
  }

  if(!argv.b) {
    console.error('no fetching block');
    process.exit(1);
  }

  if(argv.r) {
    var runsecs = parseInt(argv.r);
    if(!isNaN(runsecs)) {
      nodeSet.stopTime = new Date().getTime() + runsecs * 1000;
    }
  }
  nodeSet.run(coins||helper.netnames(), function(node) {
    node.peerman.peerLimit = 100;
    node.updateBlockChain = false;
    node.updateMempool = false;
    node.waitingBlockHash = new Buffer(argv.b, 'hex');
    node.start(argv);
    stopTime = node.stopTime;
  }, function(err) {
    if(err) throw err;
    function stopNode() {
      console.log('stopping node server\n');
      nodeSet.stop(function(){
	      console.log('stopped\n');
	      process.exit();
      });
    }
    process.on('SIGINT', stopNode);
    process.on('SIGTERM', stopNode);
    if(!isNaN(runsecs)) {
      setTimeout(stopNode, nodeSet.stopTime - (new Date().getTime()));
    }
  });
};
