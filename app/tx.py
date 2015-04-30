import time
import logging
from blockstore import BlockStoreService, ttypes
from pymongo import DESCENDING, ASCENDING
from pymongo import ReturnDocument
from bson.binary import Binary
from bson.objectid import ObjectId
from block import db2t_block
import database
from misc import get_var, set_var
from helper import generated_seconds

def get_tx_db_block(conn, dtx, db_block=None):
    bhs = dtx.get('bhs')
    if not bhs:
        return None, -1

    if db_block is not None:
        i = bhs.index(db_block['hash'])
        if i >= 0:
            return db_block, dtx['bis'][i]

    binary_bhs = [Binary(h) for h in bhs]
    bhs_map = dict((Binary(h), i) for h, i in zip(bhs, dtx['bis']))
    max_height = -1
    deepest_block = None
    block_index = -1
    for block in conn.block.find({'hash': {'$in': binary_bhs}}):
        if not block['isMain']:
            continue
        if block['height'] > max_height:
            max_height = block['height']
            deepest_block = block
            block_index = bhs_map[block['hash']]
    return deepest_block, block_index

def get_block_map(conn, txes):
    all_bhs = set([])
    for tx in txes:
        bhs = tx.get('bhs')
        if bhs:
            for h in bhs:
                all_bhs.add(h)

    if all_bhs:
        return dict((b['hash'], b)
                    for b in conn.block.find({'hash': {'$in': list(all_bhs)}}))
    else:
        return {}

def db2t_tx(conn, dtx, db_block=None):
    t = ttypes.Tx(nettype=conn.nettype)
    t.hash = dtx['hash']
    if '_id' in dtx:
        t.objId = dtx['_id'].binary

    if 'v' in dtx:
        t.version = dtx['v']

    db_block, index = get_tx_db_block(conn, dtx, db_block=db_block)
    if db_block:
        t.block = db2t_block(conn, db_block)
        t.blockIndex = index

    for i, input in enumerate(dtx['vin']):


        inp = ttypes.TxInput()
        if 'hash' in input:
            inp.hash = input['hash']
        if 'n' in input:
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

def db2t_tx_list(conn, txes):
    block_map = get_block_map(conn, txes)
    return [db2t_tx(conn, t, block_map.get(t['hash'])) for t in txes]

def t2db_tx(conn, t):
    dtx = {}
    dtx['hash'] = Binary(t.hash)
    if t.objId:
        dtx['_id'] = ObjectId(t.objId)
    dtx['vin'] = []
    dtx['vout'] = []
    if t.version is not None:
        dtx['v'] = t.version
    
    if t.block:
        dtx['bhash'] = Binary(t.block.hash)
        dtx['bindex'] = t.blockIndex

    for i, inp in enumerate(t.inputs):
        input = {}
        if inp.script is not None:
            input['s'] = Binary(inp.script)
        if inp.vout is not None:
            input['n'] = inp.vout
        if inp.hash:
            input['hash'] = Binary(inp.hash)
        if inp.q:
            input['q'] = inp.q
        if inp.address:
            input['addrs'] = inp.address.split(',')
            input['v'] = inp.amountSatoshi
        dtx['vin'].append(input)

    for i, outp in enumerate(t.outputs):
        output = {}
        if outp.address:
            output['addrs'] = outp.address.split(',')
        if outp.amountSatoshi is not None:
            output['v'] = outp.amountSatoshi
        if outp.script is not None:
            output['s'] = Binary(outp.script)
        
        dtx['vout'].append(output)
    return dtx
    
def get_tx(conn, txid):
    tx = conn.tx.find_one({'hash': Binary(txid)})
    if tx:
        return db2t_tx(conn, tx)

def get_db_tx(conn, txid, projection=None):
    if not txid:
        return None
    return conn.tx.find_one({'hash': Binary(txid)}, projection=projection)

def get_tx_list(conn, txids):
    if not txids:
        return []        
    txids = [Binary(txid) for txid in txids]
    print 'xxxxx', txids
    arr = conn.tx.find({'hash': {'$in': txids}})
    arr = list(arr)
    print 'yyyy', arr
    return db2t_tx_list(conn, arr)

def get_tail_tx_list(conn, n):
    n = min(n, 20)
    arr = list(conn.tx.find().sort({'_id': DESCENDING}).limit(n))
    arr.reverse()
    return db2t_tx_list(conn, arr)

def get_tx_list_since(conn, since):
    since_id = ObjectId(since)
    arr = list(conn.tx.find({'_id': {'$gt': since_id}}).sort({'_id': ASCENDING}).limit(20))
    return db2t_tx_list(conn, arr)

def get_missing_txid_list(conn, txids):
    if not txids:
        return []
    binary_txids = [Binary(txid) for txid in txids]
    txid_set = set(binary_txids)
    found_set = set(tx['hash'] for tx in conn.tx.find({'hash': {'$in': binary_txids}}, projection=['hash']))
    return list(txid_set - found_set)

def ensure_input_addrs(conn, dtx, input, i):
    if 'addrs' not in input and 'hash' in input:
        source_tx = get_db_tx(conn, input['hash'], projection=['hash', 'vout.addrs', 'vout.v'])
        if source_tx:
            output = source_tx['vout'][inp.vout]
            input['addrs'] = output['addrs']
            input['v'] = output['v']
            update = {}
            update['vin.%s.addrs' % i] = output.addrs
            update['vin.%s.v' % i] = output.v
            conn.tx.update({'hash': Binary(dtx['hash'])}, {'$set': update})
        return source_tx
    
def verify_tx_mempool(conn, t):
    sum_output = 0
    sum_input = 0
    for i, output in enumerate(t.outputs):
        amountSatoshi = long(output.amountSatoshi)
        sum_output += amountSatoshi
        if amountSatoshi < 546:
            return False, 'output amount too small at %s' % i

    for i, inp in enumerate(t.inputs):
        if not inp.hash:
            continue
        source_tx = get_db_tx(conn, inp.hash, projection=['hash', 'vout'])
        if not source_tx:
            return False, 'No input tx at %s' % i
        if len(source_tx['vout']) <= inp.vout:
            return False, 'No output matching %s' % i

        if generated_seconds(source_tx['_id'].generation_time) < 100 * 600:
            sb, si = get_tx_db_block(conn, source_tx)
            if si == 0:
                return False, 'Coinbase tx is too fresh to spend %s' % i            
        if not inp.address:
            output = source_tx['vout'][inp.vout]
            if output.get('w'):
                return False, 'Double spent at %s' % i
            inp.address = ','.join(output['addrs'])
            inp.amountSatoshi = output['v']
        sum_input += long(inp.amountSatoshi)
    
    fee = sum_input - sum_output
    if fee < 5000:
        return False, 'fee too small' % i                    
            
    return True, 'ok'

def verify_tx_chain(conn, t):
    for i, inp in enumerate(t.inputs):
        if not inp.hash:
            continue
        source_tx = get_db_tx(conn, inp.hash, projection=['hash', 'vout.addrs', 'vout.v'])
        if not source_tx:
            return False, 'No input tx at %s' % i
        if len(source_tx['vout']) <= inp.vout:
            return False, 'No output matching %s' % i
        if not inp.address:
            source_output = source_tx['vout'][inp.vout]
            inp.address = ','.join(source_output['addrs'])
            inp.amountSatoshi = source_output['v']
            if source_output.get('w'):
                q = {}
                q['vin.hash'] = source_tx['hash']
                q['vin.n'] = inp.vout
                ya_tx = conn.tx.find_one({'vin.hash': source_tx['hash'],
                                          'vin.n': inp.vout})
                if ya_tx:
                    ya_b, _ = get_tx_db_block(conn, ya_tx)
                    if ya_b:
                        # ya_tx is in block chain
                        return False, 'Double spent %s' %  i
                    else:
                        # ya_tx is in Mempool
                        succeed = remove_db_tx(conn, ya_tx)
                        if not succeed:
                            return False, 'Fail to remove %s for %d' % (ya_tx['hash'], i)
                else:
                    # Weird! 
                    logging.warn('Weird! output %s %d is marked as spent but no tx in the database use it', source_tx['hash'].encode('hex'), inp.vout)
                    conn.tx.update({'hash': source_tx['hash']}, {'$unset': {('vout.%d.w' % inp.vout): False}})

    return True, 'ok'

def check_removing(conn, dtx):
    b, _ = get_tx_db_block(conn, dtx)
    if b:
        logging.warn('try to delete a tx in block %s at height %d tx %s', b['hash'].encode('hex'), b['height'], dtx['hash'].encode('hex'))
        return False
    for ctx in conn.tx.find({'vin.hash': dtx['hash']}):
        if not check_removing(conn, ctx):
            return False
    return True

def do_remove_tx(conn, dtx):
    for ctx in conn.tx.find({'vin.hash': dtx['hash']}):
        do_remove_tx(conn, ctx)
    
    dtx.pop('_id', None)
    conn['removedtx'].save(dtx)
    print 'do remove tx',  dtx['hash'].encode('hex')

    conn.tx.remove({'hash': dtx['hash']})
    for input in dtx['vin']:
        if not input.get('hash'):
            continue            
        update = {}
        update['vout.%d.w' % input['n']] = False
        conn.tx.update({'hash': input['hash']}, {'$unset': update})

def remove_tx(conn, tx):
    dtx = db2t_tx(conn, tx)
    return remove_db_tx(conn, dtx)

def remove_db_tx(conn, dtx):
    if not check_removing(conn, dtx):
        return False
    do_remove_tx(conn, dtx)
    return True

def save_tx(conn, t):
    '''
    TX must be verified first
    '''
    dtx = t2db_tx(conn, t)
    txhash = dtx.pop('hash')

    bhash = dtx.pop('bhash', None)
    bindex = dtx.pop('bindex', None)
    update = {}
    if False and bhash:
        # FIXME: don't push bhs due to a bug on tokumx
        update['$push'] = {'bhs': bhash, 'bis': bindex}
    
    update['$set'] = dtx
    print 'saving', txhash.encode('hex')
    old_tx = conn.tx.find_one_and_update(
        {'hash': txhash},
        update,
        upsert=True,
        return_document=ReturnDocument.BEFORE
    )
    if not old_tx:
        # New object inserted
        conn.sendtx.update({'hash': txhash}, {'$set': {'sent': True}})
        for input in dtx['vin']:
            if not input.get('hash'):
                continue
            update = {}
            update['vout.%d.w' % input['n']] = True
            conn.tx.update({'hash': input['hash']}, {'$set': update})
    else:
        for i, output in enumerate(old_tx['vin']):
            if output.get('w'):
                update = {}
                update['vout.%d.w'] = True
                conn.tx.update({'hash': input['hash']}, {'$set': update})

# Send TX related methods
def get_sending_tx_list(conn):
    send_tx_list = []
    for sendtx in conn.sendtx.find({'sent': False}):
        stx = ttypes.SendTx()
        stx.hash = sendtx['hash']
        stx.raw = sendtx['raw']
        info = sendtx.get('info')
        if info and info.get('remoteAddress'):
            stx.remoteAddress = info['remoteAddress']
        send_tx_list.append(stx)
    return send_tx_list

def send_tx(conn, stx):
    if get_db_tx(conn, stx.hash, projection=['hash']):
        raise ttypes.AppException(code="tx_block_chain")

    if conn.sendtx.find_one({'hash': Binary(stx.hash)}):
        raise ttypes.AppException(code="sending")
    
    sendtx = {}
    sendtx['hash'] = stx.hash
    sendtx['raw'] = stx.raw
    sendtx['sent'] = False
    if stx.remoteAddress:
        sendtx['info'] = {'remoteAddress': stx.remoteAddress}
    conn.sendtx.save(sendtx)

def get_send_tx_list(conn, txids):
    send_tx_list = []
    binary_txids = [Binary(txid) for txid in txids]
    for sendtx in  conn.sendtx.find({'hash': {'$in': binary_txids}}):
        stx = ttypes.SendTx()
        stx.hash = sendtx['hash']
        stx.raw = sendtx['raw']
        info = sendtx.get('info')
        if info and info.get('remoteAddress'):
            stx.remoteAddress = info['remoteAddress']
        send_tx_list.append(stx)
    return send_tx_list

# UTXO related
def get_utxo(conn, dtx, output, i):
    utxo = ttypes.UTXO()
    utxo.address = output['addrs'][0]
    utxo.amountSatoshi = output['v']
    utxo.txid = dtx['hash']
    utxo.vout = i
    utxo.scriptPubKey = output['s']

    b, index = get_tx_db_block(conn, dtx)
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
    output_txes = conn.tx.find({'oa': {'$in': addresses}}, projection=['hash', 'vout'])
    input_txes =  conn.tx.find({'ia': {'$in': addresses}}, projection=['hash', 'vin'])

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
            {'oa': {'$in': addresses}},
            {'ia': {'$in': addresses}}]},
                               projection=['hash'])
    return [tx['hash'] for tx in txes]


def get_related_tx_list(conn, addresses):
    addr_set = set(addresses)
    arr = conn.tx.find({
        '$or': [
            {'oa': {'$in': addresses}},
            {'ia': {'$in': addresses}}]})
    return db2t_tx_list(conn, arr)
    
def update_addrs(conn, dtx):
    update = {}
    if 'oa' not in dtx:
        oa = set([])
        for output in dtx['vout']:
            addrs = output.get('addrs')
            if addrs:
                for a in addrs:
                    oa.add(a)
        if oa:
            update['oa'] = list(oa)

    if 'ia' not in dtx:
        ia = set([])
        for input in dtx['vin']:
            addrs = input.get('addrs')
            if addrs:
                for a in addrs:
                    ia.add(a)
        if ia:
            update['ia'] = list(ia)
    if update:    
        conn.tx.update({'hash': dtx['hash']}, {'$set': update})

def update_vin_hash(conn, dtx):
    update = {}
    
    if 'vh' not in dtx:
        hs = set([])
        for input in dtx['vin']:
            vh = input.get('hash')
            if vh:
                hs.add(vh)
        if hs:
            update['vh'] = list(hs)
    if update:    
        conn.tx.update({'hash': dtx['hash']}, {'$set': update})
