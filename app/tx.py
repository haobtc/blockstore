import time
from blockstore import BlockStoreService, ttypes
from pymongo import DESCENDING, ASCENDING
from bson.binary import Binary
from bson.objectid import ObjectId
import database

def get_tx_db_block(conn, dtx):
    if not dtx.get('bhs'):
        return None

    binary_bhs = [Binary(h) for h in dtx['bhs']]
    max_height = -1
    deepest_block = None
    for block in conn.block.find({'hash': {'$in': binary_bhs}}):
        if not block.isMain:
            continue
        if block.height > max_height:
            max_height = block.height
            deepest_block = block
    return deepest_block
    
def db2t_tx(conn, dtx):
    t = ttypes.Tx()
    t.txid = dtx['hash']
    if '_id' in dtx:
        t.objId = dtx['_id'].binary
        
    if dtx.get('bhs'):
        binary_bhs = [Binary(h) for h in dtx['bhs']]
        bimap = dict(zip(dtx['bhs'], dtx['bis']))

        block = get_tx_db_block(conn, dtx)
        if block:
            t.blockHash = block['hash']
            t.blockIndex = bimap[block['hash']]

    for i, input in enumerate(dtx['vin']):
        inp = ttypes.TxInput()
        inp.txid = input['hash']
        inp.vout = input['n']
        inp.script = input['s']
        if 'q' in input:
            inp.q = input['q']

        ensure_input_addrs(conn, dtx, input, i)
        if input.get('addrs'):
            inp.address = ','.join(input['addrs'])
            inp.amountSatoshi = input['v']
        t.inputs.append(inp)

    for output in dtx['vout']:
        outp = ttypes.TxOutput()
        outp.address = ','.join(output['addrs'])
        outp.amountSatoshi = output['v']
        outp.script = output['s']
        t.outputs.append(outp)
    return t

def t2db_tx(conn, t):
    dtx = {}
    dtx['hash'] = t.txid
    dtx['_id'] = ObjectId(t.objid)
    dtx['vin'] = []
    dtx['vout'] = []
    if t.blockhash:
        dtx['bhash'] = t.blockHash
        dtx['bindex'] = t.blockIndex

    for i, inp in enumerate(t.inputs):
        input = {}
        input['s'] = inp.script
        input['n'] = inp.vout
        input['hash'] = inp.txid
        if inp.q:
            input['q'] = inp.q
        if inp.address:
            input['addrs'] = inp.address.split(',')
            input['v'] = inp.amountSatoshi
        dtx['vin'].append(input)

    for i, outp in enumerate(t.outputs):
        output = {}
        output['addrs'] = outp.address.split(',')
        output['v'] = outp.amountSatoshi
        output['s'] = outp.script
        dtx['vout'].append(output)
    return dtx
    
def get_tx(conn, txid):
    tx = conn.tx.find_one({'hash': Binary(txid)})
    if tx:
        return db2t_tx(conn, tx)

def get_db_tx(conn, txid, projection=None):
    return conn.tx.find_one({'hash': Binary(txid)}, projection=projection)

def get_tx_list(conn, txids):
    if not txids:
        return []        
    txids = [Binary(txid) for txid in txids]
    return [db2t_tx(conn, t) for t in conn.tx.find({'hash', {'$in': txids}})]

def get_latest_tx_list(conn):
    arr = list(conn.tx.find().sort({'_id': DESCENDING}).limit(20))
    arr.reverse()
    return [db2t_tx(conn, t) for t in arr]

def get_tx_list_since(conn, since):
    since_id = ObjectId(since)
    arr = list(conn.tx.find({'_id': {'$gt': since_id}}).sort({'_id': ASCENDING}).limit(20))
    return [db2t_tx(conn, t) for t in arr]

def get_missing_txid_list(conn, txids):
    if not txids:
        return []
    binary_txids = [Binary(txid) for txid in txids]
    txid_set = set(binary_txids)
    found_set = set(tx['hash'] for tx in conn.tx.find({'hash': {'$in': binary_txids}}, projection=['hash']))
    return list(txid_set - found_set)

def ensure_input_addrs(conn, dtx, input, i):
    if 'addrs' not in input:
        input_tx = get_db_tx(conn, input['hash'], projection=['hash', 'vout.addrs', 'vout.v'])
        if input_tx:
            output = input_tx['vout'][inp.vout]
            input['addrs'] = output['addrs']
            input['v'] = output['v']
            update = {}
            update['vin.%s.addrs' % i] = output.addrs
            update['vin.%s.v' % i] = output.v
            conn.tx.update({'hash': Binary(dtx['hash'])}, {'$set': update})
        return input_tx
    
def verify_tx(conn, t, soft=False):
    for i, output in enumerate(t.outputs):
        amountSatoshi = long(output.amountSatoshi)
        if not soft and amountSatoshi < 546:
            return False, 'output amount too small at %s' % i

    for i, inp in enumerate(t.inputs):
        input_tx = get_db_tx(conn, inp.txid, projection=['hash', 'vout.addrs', 'vout.v'])
        if not input_tx:
            return False, 'No input tx at %s' % i
        if len(input_tx['vout']) <= inp.vout:
            return False, 'No output matching %s' % i
        if not inp.address:
            output = input_tx['vout'][inp.vout]

            inp.address = ','.join(output['addrs'])
            inp.amountSatoshi = output['v']
    return True, 'ok'

def save_tx(conn, t):
    '''
    TX must be verified first
    '''
    #dtx = get_db_tx(conn, t.txid, projection=['hash'])
    #if dtx:
    #    if t.blockHash:
    #        assert not not t.blockIndex
    #        conn.tx.update({'hash': Binary(t.txid)},
    #                       {'$push': {'bhs': t.blockHash, 'bis': t.blockIndex}})
    #else:
    dtx = t2db_tx(conn, t)
    txhash = dtx.pop('hash', None)
    bhash = dtx.pop('bhash', None)
    bindex = dtx.pop('bindex', None)
    update = {}
    if bhash:
        update['$push'] = {'bhs': bhash, 'bis': bindex}
    update['$set'] = dtx
    old_tx = conn.tx.find_one_and_update(
        {'hash': Binary(txhash)},
        update,
        upsert=True,
        return_document=ReturnDocument.BEFORE
    )
    if not old_tx:
        # New object inserted
        conn.update({'hash': Binary(txhash)}, {'$set': {'sent': true}})

# Send TX related methods
def get_sending_tx_list(conn):
    send_tx_list = []
    for sendtx in conn.sendtx.find({'sent': false}):
        stx = ttypes.SendTx()
        stx.txid = sendtx['hash']
        stx.raw = sendtx['raw']
        info = sendtx.get('info')
        if info and info.get('remoteAddress'):
            stx.remoteAddress = info['remoteAddress']
        send_tx_list.append(stx)
    return send_tx_list

def send_tx(conn, stx):
    if get_db_tx(conn, stx.txid, projection=['hash']):
        raise ttypes.AppException(code="tx_block_chain")

    if conn.sendtx.find_one({'hash': Binary(stx.txid)}):
        raise ttypes.AppException(code="sending")
    
    sendtx = {}
    sendtx['hash'] = stx.txid
    sendtx['raw'] = stx.raw
    sendtx['sent'] = False
    if stx.remoteAddress:
        sendtx['info'] = {'remoteAddress': stx.remoteAddress}
    conn.sendtx.save(sendtx)

# UTXO related
def get_utxo(conn, dtx, output, i):
    utxo = ttypes.UTXO()
    utxo.address = output['addrs'][0]
    utxo.amountSatoshi = output['v']
    utxo.txid = dtx['hash']
    utxo.vout = i
    utxo.scriptPubKey = output['s']

    b = get_tx_db_block(conn, dtx)
    if b:
        tip = get_tip_block(conn)
        utxo.confirmations = tip.height - b['height'] + 1
        utxo.timestamp = b.timestamp
    else:
        utxo.confirmations = 0
        utxo.timestamp = long(time.mktime(dtx['_id'].generation_time.utctimetuple()))
    return utxo

def get_unspent(conn, addresses):
    addr_set = set(addresses)
    output_txes = conn.tx.find({'vout.addrs': {'$in': addresses}}, projection=['hash', 'vout'])
    input_txes =  conn.tx.find({'vin.addrs': {'$in': addresses}}, projection=['hash', 'vin'])

    utxos = []
    spent_set = set([])
    for dtx in input_txes:
        for input in dtx['vin']:
            if not input.get('addrs'):
                continue
            # FIXME: consider multiple addrs
            addr = input['addrs'][0]
            if addr in addr_set:
                spent_set.add((input['hash'], input['n']))
    
    for dtx in output_txes:
        for i, output in enumerate(dtx['vout']):
            if not output.get('addrs'):
                continue
            #FIXME: consider multiple addrs
            addr = output['addrs'][0]
            if (dtx['hash'], i) not in spent_set:
                utxos.append(get_utxo(conn, dtx, output, i))
    return utxos

def get_related_txid_list(conn, addresses):
    addr_set = set(addresses)
    txes = conn.tx.find({
        '$or': [
            {'vout.addrs': {'$in': addresses}},
            {'vin.addrs': {'$in': addresses}}]},
                               projection=['hash'])
    return [tx['hash'] for tx in txes]


def get_related_tx_list(conn, addresses):
    addr_set = set(addresses)
    arr = conn.tx.find({
        '$or': [
            {'vout.addrs': {'$in': addresses}},
            {'vin.addrs': {'$in': addresses}}]})
    return [db2t_tx(conn, t) for t in arr]
    
    
