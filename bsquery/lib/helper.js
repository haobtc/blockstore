var buffertools    = require('buffertools');
var bitcore = require('bitcore-multicoin');
var config = require('./config');
var Script = bitcore.Script;
var util = bitcore.util;

module.exports.reverseBuffer = function(hash) {
  var reversed = new Buffer(hash.length);
  hash.copy(reversed);
  buffertools.reverse(reversed);
  return reversed;
}

module.exports.toBuffer = function(hash) {
  if(hash instanceof mongodb.Binary) {
    return hash.buffer;
  } else if(hash instanceof Buffer) {
    return hash;
  } else {
    return new Buffer(hash, 'hex');
  }
};

module.exports.clone = function(src) {
  var dest = new Object();
  for(var key in src) {
    dest[key] = src[key];
  }
  return dest;
}

module.exports.satoshiToNumberString = function(v) {
  if(!v || v == '0') {
    return '0'
  }
  while(v.length < 8) {
    v = '0' + v;
  }
  v = v.replace(/\d{8}$/, '.$&').replace(/0+$/, '').replace(/\.$/, '.0');
  if(v.substr(0, 1) == '.') {
    v = '0' + v;
  }
  return v;
};

module.exports.sendJSONP = function(req, res, obj) {
  if(req.start) {
    var time = Date.now() - req.start;
    console.info('request', req.method, req.path, 'takes', time/1000.0, 'seconds');
  }

  if(req.query.callback && /^\w+$/.test(req.query.callback)) {
    res.set('Content-Type', 'text/javascript');
    res.send(req.query.callback + '(' + JSON.stringify(obj) + ');');
  } else {
    res.set('Content-Type', 'application/json');
    res.send(obj);
  }
};


module.exports.netnames = function() {
  var netnames = [];
  for(var netname in config.networks) {
    if(config.networks.hasOwnProperty(netname)) {
      netnames.push(netname);
    }
  }
  return netnames;
};

module.exports.processTx = function(netname, tx, idx, blockObj) {
  var txObj = {};
  if(idx >= 0) {
    txObj.bidx = idx;
  }
  txObj.hash = module.exports.reverseBuffer(tx.hash);
  if(blockObj) {
    txObj.bhash = blockObj.hash;
  }
  if(tx.version != 1) {
    txObj.v = tx.version;
  }
  if(tx.lock_time != 0) {
    txObj.lock_time = tx.lock_time;
  }
  txObj.vin = tx.ins.map(function(input, i) {
    var txIn = {};
    var n = input.getOutpointIndex();
    if(n >= 0) {
      txIn.hash = module.exports.reverseBuffer(new Buffer(input.getOutpointHash()));
      txIn.n = n;
      
      txIn.k = txIn.hash.toString('hex') + '#' + n;
    }
    txIn.s = input.s;
    txIn.q = input.q;
    return txIn;
  });

  txObj.vout = tx.outs.map(function(out, i) {
    var txOut = {};
    txOut.s = out.s;
    if(tx.outs[i].s) {
      var script = new Script(tx.outs[i].s);
      txOut.addrs = script.getAddrStr(netname);
    }
    txOut.v = util.valueToBigInt(out.v).toString();
    return txOut;
  });
  return txObj;
};

module.exports.dictlize = function(arr, keyfn) {
  var dict = {};
  arr.forEach(function(obj) {
    var key = keyfn(obj);
    if(key != undefined) {
      dict[key] = obj;
    }
  });
  return dict;
};

function Skip(message) {
  this.message = message;
}
module.exports.Skip = Skip;

function UserError(code, message) {
  this.code = code;
  this.message = message;
}

module.exports.UserError = UserError;
