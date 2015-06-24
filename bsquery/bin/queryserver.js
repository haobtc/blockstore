var express = require('express');

var cluster = require('cluster');
var http = require('http');
var bitcore = require('bitcore-multicoin');
var config = require('../lib/config');
var async = require('async');
var app = express();
var bodyParser = require('body-parser');
var Query = require('../lib/Query');
var helper = require('../lib/helper');
var blockstore = require('../lib/blockstore');
var queryapiv1 = require('../lib/queryapiv1');
var queryapiv2 = require('../lib/queryapiv2');

app.use(bodyParser());

app.use('/explorer/', express.static('public'));

app.use(function(req, res, next) {
  req.start = Date.now();
  next();
});

queryapiv1.installAPI(app);
queryapiv2.installAPI(app);

app.use(function(err, req, res, next){
  if(err instanceof blockstore.ttypes.AppException) {
    res.status(400).send({code: err.code, error: err.message});
  } else if(err instanceof helper.UserError) {
    res.status(400).send({code: err.code, error: err.message});
  } else {
    console.error('EEE', err, err.stack);
    res.status(500).send({error: err.message});
  }
});

function startServer(argv){
  var netnames = argv.c;
  if(typeof netnames == 'string') {
    netnames = [netnames];
  }
  netnames = netnames || helper.netnames();
  var server = http.Server(app);
  server.listen(argv.p || 9000, argv.h || '0.0.0.0');

  setTimeout(function() {
    server.close(function() {
      process.exit();
    });
//  }, 5000 + Math.random() * 2000);
  }, 360 * 1000 + Math.random() * 60000);

  setTimeout(function() {
    blockstore.keepTip();
  }, Math.random() * 3000);
}

module.exports.start = function(argv){
  var numWorkers = argv.n || 1;
  numWorkers = parseInt(numWorkers);
  var workers = [];
  if(cluster.isMaster) {
    console.info('start', numWorkers, 'workers');
    for(var i=0; i<numWorkers; i++) {
      var worker = cluster.fork();
      workers.push(worker);
    }
    cluster.on('exit', function(worker, code, signal) {
      console.log(new Date(), 'work ' + worker.process.pid + ' died');
      if(!worker.suicide) {
	for(var i = 0; i<workers.length; i++) {
	  if(workers[i].id == worker.id) {
	    workers[i] = cluster.fork();
	    console.log(new Date(), 'worker ', workers[i].process.pid, 'retarted');
	    break;
	  }
	}
      }
    });
  } else {
    startServer(argv);
  }
};
