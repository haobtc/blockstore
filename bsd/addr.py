import logging
import database
from struct import pack

from blockstore import BlockStoreService, ttypes
from collections import defaultdict
from tx import get_tx_db_block, ensure_input_addrs, get_db_tx
from pymongo import ReturnDocument
from bson.binary import Binary
from bson.objectid import ObjectId
from bson.errors import InvalidId
from misc import itercol

class TxStat:
    def __init__(self):
        self.input_amount = 0
        self.output_amount = 0
        self.remove_utxos = []
        self.add_utxos = []
        
def gen_tx_stats(conn, dtx, force_new_tx=False, filter_addrs=None):
    vin = dtx.get('vin', [])
    changes = defaultdict(TxStat)
    for input_index, input in enumerate(vin):
        ensure_input_addrs(conn, dtx, input, input_index)
        addrs = input.get('addrs')
        if addrs:
            # TODO: consider multiple addresses
            addr = addrs[0]
            txstat = changes[addr]
            uref = Binary('#'.join([input['hash'], pack('>I', input['n'])]))
            txstat.remove_utxos.append(uref)
            txstat.input_amount += long(input['v'])
    
    for i, output in enumerate(dtx.get('vout', [])):
        addrs = output.get('addrs')
        if addrs:
            addr = addrs[0]
            spt = output.get('w', False)
            txstat = changes[addr]
            if not spt:
                uref = Binary('#'.join([dtx['hash'], pack('>I', i)]))
                txstat.add_utxos.append(uref)
            txstat.output_amount += long(output['v'])
            
    if filter_addrs:
        new_changes = {}
        for addr, txstat in changes.iteritems():
            if addr in filter_addrs:
                new_changes[addr] = txstat
        changes = new_changes

    for addr, txstat in changes.iteritems():
        query = {'a': addr, 't': dtx['hash']}
        update = {'$set': {'i': txstat.input_amount, 'o': txstat.output_amount}}
        #conn.addrtx.update(query, update, upsert=True)
        old_tx = conn.addrtx.find_one_and_update(query, update, upsert=True, return_document=ReturnDocument.BEFORE)
        query = {'_id': addr}
        update = {'$set': {}}
        if not old_tx or force_new_tx:
            # new tx
            update['$inc'] = {
                'r': txstat.output_amount,                          # received
                'b': txstat.output_amount - txstat.input_amount,    # balance
                'n': 1                                              # number of txes
            }

        if txstat.add_utxos:
            update['$addToSet'] = {'u': {'$each': txstat.add_utxos}}
        
        conn.addrstat.update(query, update, upsert=True)
        if txstat.remove_utxos:
            update = {}
            update['$pullAll'] = {'u': txstat.remove_utxos}
            conn.addrstat.update(query, update)

        query = {'a': addr, 't': dtx['hash']}
        update = {'$set': {'i': txstat.input_amount, 'o': txstat.output_amount}}
        #conn.addrtx.update(query, update, upsert=True)
        conn.addrtx.find_one_and_update(query, update, upsert=True, return_document=ReturnDocument.BEFORE)
        

def undo_tx_stats(conn, dtx):
    changes = defaultdict(TxStat)
    for input in dtx.get('vin', []):
        addrs = input.get('addrs')
        if addrs:
            # TODO: consider multiple addresses
            addr = addrs[0]
            txstat = changes[addr]
            txstat.input_amount += long(input['v'])

            src_dtx = get_db_tx(conn, input['hash'])
            if src_dtx:
                src_output = src_dtx['vout'][input['n']]
                if src_output:
                    spt = src_output.get('w', False)
                    if not spt:
                        uref = Binary('#'.join([input['hash'], pack('>I', input['n'])]))
                        txstat.add_utxos.append(uref)
    
    for i, output in enumerate(dtx.get('vout', [])):
        addrs = output.get('addrs')
        if addrs:
            addr = addrs[0]
            txstat = changes[addr]
            uref = Binary('#'.join([dtx['hash'], pack('>I', i)]))
            txstat.remove_utxos.append(uref)
            txstat.output_amount += long(output['v'])

    for addr, txstat in changes.iteritems():
        addrtx = conn.addrtx.find_one({'a': addr, 't': dtx['hash']})
        if not addrtx:
            continue

        conn.addrtx.remove({'a': addrtx['_id']})

        query = {'_id': addr, 't': dtx['hash']}
        update = {}
        update['$inc'] = {'r': -txstat.output_amount,
                          'n': -1,
                          'b': txstat.input_amount - txstat.output_amount}

        if txstat.remove_utxos:
            update['$pullAll'] = {'u': txstat.remove_utxos}
        conn.addrstat.update(query, update)

        if txstat.add_utxos:
            update = {}
            update['$pushAll'] = {'u': txstat.add_utxos}
            conn.addrstat.update(query, update)

# watched address
def watch_addresses(conn, group, addresses):
    for address in addresses:
        record = {'a': address, 'g': group}
        if not conn.watchedaddr.find_one(record):
            conn.watchedaddr.insert(record)
            for addrtx in conn.addrtx.find({'a': address}).batch_size(30):
                watch_addrtx(conn, addrtx)

def watch_addrtx(conn, addrtx):
    wa = conn.watchedaddr.find_one({'a': addrtx['a']})
    if wa:
        addrtx.pop('_id', None)
        conn.watchedaddrtx.update({'a': addrtx['a'], 't': addrtx['t']}, 
                                  {'$set': addrtx},
                                  upsert=True)
    
def unwatch_tx(conn, dtx):
    conn.watchedaddrtx.remove({'t': dtx['hash']})

def get_watching_list(conn, group, count=20, cursor=None):
    query = {}
    if cursor:
        try:
            cursor = ObjectId(cursor)
            query = {'_id': {'$gt': cursor}}
        except InvalidId:
            pass

    watching_list = ttypes.TxIdListWithCursor()
    watching_list.txids = []

    limit = max(count * 2, 1000)
    for wat in conn.watchedaddrtx.find(query).batch_size(30).sort('_id').limit(limit):
        watching_list.cursor = wat['_id'].binary
        if conn.watchedaddr.find_one({'a': wat['a'], 'g': group}):
            if wat['t'] not in watching_list.txids:
                watching_list.txids.append(wat['t'])
                if len(watching_list.txids) >= count:
                    break
    return watching_list

def get_addr_stat_list(conn, addresses):
    if not addresses:
        return []

    addr_stat_list = []
    for addrstat in conn.addrstat.find({'_id': {'$in': addresses}}, projection=['_id', 'n', 'r', 'b']).batch_size(30):
        stat = ttypes.AddrStat()
        stat.address = addrstat['_id']
        stat.receivedSatoshi = str(addrstat['r'])
        stat.balanceSatoshi = str(addrstat['b'])
        stat.cntTxes = addrstat['n']
        addr_stat_list.append(stat)
    return addr_stat_list

