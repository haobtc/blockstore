import database
from struct import pack

from collections import defaultdict
from tx import get_tx_db_block
from pymongo import ReturnDocument
from bson.binary import Binary
import leveldb

class TxStat:
    def __init__(self):
        self.input_amount = 0
        self.output_amount = 0
        self.remove_utxos = []
        self.add_utxos = []
        
def gen_tx_stats(conn, dtx):
    changes = defaultdict(TxStat)
    for input in dtx.get('vin', []):
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
            txstat = changes[addr]
            uref = Binary('#'.join([dtx['hash'], pack('>I', i)]))
            txstat.add_utxos.append(uref)
            txstat.output_amount += long(output['v'])

    for addr, txstat in changes.iteritems():
        query = {'_id': addr}
        update = {}
        update['$inc'] = {
            'r': txstat.output_amount,                          # received
            'b': txstat.output_amount - txstat.input_amount,    # balance
            'n': 1                                              # number of txes
        }

        if txstat.add_utxos:
            update['$pushAll'] = {'u': txstat.add_utxos}
        
        conn.addrstat.update(query, update, upsert=True)
        if txstat.remove_utxos:
            update = {}
            update['$pullAll'] = {'u': txstat.remove_utxos}
            conn.addrstat.update(query, update)

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
            txstat = changes[addr]
            uref = Binary('#'.join([input['hash'], pack('>I', input['n'])]))
            txstat.add_utxos.append(uref)
            txstat.input_amount += long(input['v'])
    
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

        conn.addrtx.remove({_id: addrtx['_id']})

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

