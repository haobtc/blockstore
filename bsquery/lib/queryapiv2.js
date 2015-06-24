'use strict';

var underscore = require('underscore');
var bitcore = require('bitcore-multicoin');
var config = require('./config');
var async = require('async');

var Query = require('./Query');

var blockstore = require('./blockstore');
var helper = require('./helper');

var sendJSONP = helper.sendJSONP;

var URL_PREFIX = '/queryapi/v2';

module.exports.installAPI = function(app) {
  // Get unspent
  app.use(URL_PREFIX + '/unspent/',   function getUnspent(req, res) {
    var addressList = Query.parseAddressList(req);
    Query.getUnspentV1(addressList, function(err, results) {
      if(err) throw err;
      sendJSONP(req, res, results);
    });
  });

  app.use(URL_PREFIX + '/address/stats/', function(req, res, next) {
    var addressList = Query.parseAddressList(req);
    Query.getAddrStatList(addressList, function(err, arr) {
      if(err) return next(err);
      return sendJSONP(req, res, arr);
    });
  });

  app.use(URL_PREFIX + '/tx/list/', function(req, res, next) {
    var addressList = Query.parseAddressList(req);
    var count = parseInt(req.query.count);
    if(isNaN(count) || count <= 0 || count > 50) {
      count = 50;
    }

    var cursor = req.query.cursor || null;
    var useDetail = underscore.contains(['1', 'yes', 'true'], req.query.detail);
    Query.getRelatedTxIdList(addressList, cursor, count, useDetail, function(err, arr) {
      if(err) return next(err);
      return sendJSONP(req, res, arr);
    });
  });  
};
