import database
from struct import pack
from collections import defaultdict
from tx import get_tx_db_block
from pymongo import ReturnDocument
import leveldb

class TxStat:
    def __init__(self):
        self.input_amount = 0
        self.output_amount = 0
        
def gen_tx_stats(conn, dtx):
    changes = defaultdict(TxStat)
    for input in dtx.get('vin', []):
        addrs = input.get('addrs')
        if addrs:
            # TODO: consider multiple addresses
            addr = addrs[0]
            changes[addr].input_amount += long(input['v'])
    
    for output in dtx.get('vout', []):
        addrs = output.get('addrs')
        if addrs:
            addr = addrs[0]
            changes[addr].output_amount += long(output['v'])
        
    for addr, txstat in changes.iteritems():
        query = {'_id': addr}
        update = {}
        update['$inc'] = {
            'r': txstat.output_amount,                          # received
            'b': txstat.output_amount - txstat.input_amount,    # balance
            'n': 1                                              # number of txes
        }
        conn.addrstat.update(query, update, upsert=True)
        query = {'a': addr, 't': dtx['hash']}
        update = {'$set': {'i': txstat.input_amount, 'o': txstat.output_amount}}
        conn.addrtx.update(query, update, upsert=True)
        

def undo_tx_stats(conn, dtx):
    changes = defaultdict(TxStat)
    for input in dtx.get('vin', []):
        addrs = input.get('addrs')
        if addrs:
            # TODO: consider multiple addresses
            addr = addrs[0]
            changes[addr].input_amount += long(input['v'])
    
    for output in dtx.get('vout', []):
        addrs = output.get('addrs')
        if addrs:
            addr = addrs[0]
            changes[addr].output_amount += long(output['v'])
            
    for addr, txstat in changes.iteritems():
        addrtx = conn.addrtx.find_one({'a': addr, 't': dtx['hash']})
        if not addrtx:
            continue

        conn.addrtx.remove({_id: addrtx['_id']})

        query = {'_id': addr, 't': dtx['hash']}
        update = {}
        update['$inc'] = {'r': -txstat.output_amount,
                          'n': -1,
                          'b': txstat.input_amount - txstat.output_amount}
        conn.addrstat.update(query, update)
