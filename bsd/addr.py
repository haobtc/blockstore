import database
from collections import defaultdict

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
        update['$push'] = {'t': dtx['hash']}
        update['$inc'] = {'r': txstat.output_amount,                          # received
                          'b': txstat.output_amount - txstat.input_amount}    # balance
        conn.addr.update(query, update, upsert=True)

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
        query = {'_id': addr, 't': dtx['hash']}
        update = {}
        update['$pullAll'] = {'t': dtx['hash']}
        update['$inc'] = {'r': -txstat.output_amount,
                          'b': txstat.input_amount - txstat.output_amount}
        conn.addr.update(query, update)
