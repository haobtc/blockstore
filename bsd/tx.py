import time
import pytz
import logging
from struct import unpack
from blockstore import BlockStoreService, ttypes
from pymongo import DESCENDING, ASCENDING
from pymongo import ReturnDocument
from bson.binary import Binary
from bson.objectid import ObjectId
from block import db2t_block
import database
from misc import get_var, set_var, get_dbobj_list
from block import get_tip_block
from helper import generated_seconds, get_nettype, get_netname
from helper import get_netname, fee_rate_satoshi, minimum_fee_satoshi

def get_tx_db_block(conn, dtx, db_block=None):
    if 'bhs' in dtx:
        bhs = dtx['bhs']
        bis = dtx['bis']
    else:
        rels = list(conn.txblock.find({'t': dtx['hash']}))
        bhs = [v['b'] for v in rels]
        bis = [v['i'] for v in rels]

    if not bhs:
        return None, -1

    if db_block is not None:
        i = bhs.index(db_block['hash'])
        if i >= 0:
            return db_block, bis[i]

    bhs_map = dict(zip(bhs, bis))
    max_height = -1
    deepest_block = None
    block_index = -1
    for block in get_dbobj_list(conn, conn.block, bhs):
        if not block['isMain']:
            continue
        if block['height'] > max_height:
            max_height = block['height']
            deepest_block = block
            block_index = bhs_map[block['hash']]
    return deepest_block, block_index

def get_block_map(conn, dtxs):
    txids = [dtx['hash'] for dtx in dtxs]
    bh_set = set(v['b'] for v in conn.txblock.find({'t': {'$in': txids}}))
    
    bmap = {}
    for b in get_dbobj_list(conn, conn.block, list(bh_set)):
        bmap[b['hash']] = b
    return bmap

def db2t_tx(conn, dtx, db_block=None, tblock=None, ensure_input=True):
    t = ttypes.Tx(nettype=get_nettype(conn))
    t.hash = dtx['hash']
    if '_id' in dtx:
        t.objId = dtx['_id'].binary

    if 'v' in dtx:
        t.version = dtx['v']

    db_block, index = get_tx_db_block(conn, dtx, db_block=db_block)
    if db_block:
        if tblock:
            t.block = tblock
            t.blockIndex = index
        else:
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

        if ensure_input:
            ensure_input_addrs(conn, dtx, input, i)
            if input.get('addrs'):
                inp.address = ','.join(input['addrs'])
                inp.amountSatoshi = input['v']
        t.inputs.append(inp)

    for output in dtx['vout']:
        outp = ttypes.TxOutput()
        outp.address = ','.join(output.get('addrs', []))
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
    
def get_db_tx_list_in_block(conn, block_hash):
    rels = conn.txblock.find({'b': Binary(block_hash)}).sort('id')
    tx_hash_list = [r['t'] for r in rels]
    return get_dbobj_list(conn, conn.tx,
                          tx_hash_list,
                          keep_order=True)

def get_tx(conn, txid):
    tx = conn.tx.find_one({'hash': Binary(txid)})
    if tx:
        return db2t_tx(conn, tx)

def get_db_tx(conn, txid, projection=None):
    if not txid:
        return None
    return conn.tx.find_one({'hash': Binary(txid)}, projection=projection)

def get_tx_list(conn, txids, keep_order=False):
    arr = get_db_tx_list(conn, txids, keep_order=keep_order)
    return db2t_tx_list(conn, arr)

def get_db_tx_list(conn, txids, keep_order=False):
    txids = [Binary(txid) for txid in txids]
    return get_dbobj_list(conn, conn.tx, txids, keep_order=keep_order)

def get_tail_tx_list(conn, n):
    n = min(n, 20)
    arr = list(conn.tx.find().sort([('_id', DESCENDING)]).limit(n))
    arr.reverse()
    return db2t_tx_list(conn, arr)

def get_tx_list_since(conn, since, n=20):
    since_id = ObjectId(since)
    arr = list(conn.tx.find({'_id': {'$gt': since_id}}).sort([('_id', ASCENDING)]).limit(n))
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
            output = source_tx['vout'][input['n']]
            update = {}
            if 'addrs' in output:
                input['addrs'] = output['addrs']
                update['vin.%s.addrs' % i] = output['addrs']
            if 'v' in output:
                input['v'] = output['v']
                update['vin.%s.v' % i] = output['v']
            if update:
                conn.tx.update({'hash': Binary(dtx['hash'])}, {'$set': update})
        return source_tx
    
def verify_tx_mempool(conn, t):
    if get_db_tx(conn, t.hash):
        return True, 'ok'
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
            return False, 'No input tx at %s for %s' % (i, inp.hash.encode('hex'))
        if len(source_tx['vout']) <= inp.vout:
            return False, 'No output matching %s' % i

        if generated_seconds(source_tx['_id'].generation_time) < 100 * 600:
            sb, si = get_tx_db_block(conn, source_tx)
            if si == 0:
                return False, 'Coinbase tx is too fresh to spend %s' % i            
        if not inp.address:
            output = source_tx['vout'][inp.vout]
            if output.get('w'):
                logging.warn('Double spent for %s at input %s with source %s at %s', t.hash.encode('hex'), i, source_tx['hash'].encode('hex'), inp.vout)
                return False, 'Double spent at %s with %s' % (i, inp.hash.encode('hex'))
            inp.address = ','.join(output['addrs'])
            inp.amountSatoshi = output['v']
        sum_input += long(inp.amountSatoshi)
    
    fee = sum_input - sum_output
    if fee < 0.5 * minimum_fee_satoshi(get_netname(conn)):
        return False, 'fee too small %s at tx %s' % (fee, t.hash.encode('hex'))
            
    return True, 'ok'

def verify_tx_chain(conn, t):
    if get_db_tx(conn, t.hash):
        return True, 'ok'

    for i, inp in enumerate(t.inputs):
        if not inp.hash:
            continue
        source_tx = get_db_tx(conn, inp.hash, projection=['hash', 'vout.addrs', 'vout.v'])
        if not source_tx:
            return False, 'No input tx at %s for %s' % (i, inp.hash.encode('hex'))
        if len(source_tx['vout']) <= inp.vout:
            return False, 'No output matching %s' % i
        if not inp.address:
            source_output = source_tx['vout'][inp.vout]
            #print source_output, source_tx['hash'].encode('hex')
            if 'addrs' in source_output:
                inp.address = ','.join(source_output['addrs'])
            if 'v' in source_output:
                inp.amountSatoshi = source_output['v']
            if source_output.get('w'):
                ya_tx = conn.tx.find_one({'vh': source_tx['hash'],
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
        #logging.warn('try to delete a tx in block %s at height %d tx %s', b['hash'].encode('hex'), b['height'], dtx['hash'].encode('hex'))
        return False
    for ctx in conn.tx.find({'vh': dtx['hash']}):
        if not check_removing(conn, ctx):
            return False
    return True

def do_remove_tx(conn, dtx):
    for ctx in conn.tx.find({'vh': dtx['hash']}):
        do_remove_tx(conn, ctx)

    for input in dtx['vin']:
        if not input.get('hash'):
            continue            
        update = {}
        update['vout.%d.w' % input['n']] = False
        conn.tx.update({'hash': input['hash']}, {'$unset': update})
    
    dtx.pop('_id', None)
    conn['removedtx'].save(dtx)
    #print 'do remove tx',  dtx['hash'].encode('hex')
    conn.txblock.remove({'t': dtx['hash']})
    conn.sendtx.remove({'hash': dtx['hash']})
    # conn.sendtx.update({'hash': dtx['hash']}, 
    #                    {'$set': {'sent': True,
    #                              'by_removed': True}})
    conn.tx.remove({'hash': dtx['hash']})
    logging.info('removed tx %s', dtx['hash'].encode('hex'))

    remove_dep(conn, dtx)

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
    dtx.pop('_id', None)
    txhash = dtx.pop('hash')

    bhash = dtx.pop('bhash', None)
    bindex = dtx.pop('bindex', None)
    update = {}
    update['$set'] = dtx

    old_tx = conn.tx.find_one_and_update(
        {'hash': txhash},
        update,
        upsert=True,
        return_document=ReturnDocument.BEFORE
    )
    if not old_tx:
        # New object inserted
        #conn.sendtx.update({'hash': txhash}, {'$set': {'sent': True}})
        #logging.debug('added %s tx %s', get_netname(conn), txhash.encode('hex'))
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
        if info and info.get('sequence'):
            stx.sequence = info['sequence']

        send_tx_list.append(stx)
    return send_tx_list

def send_tx(conn, stx):
    if get_db_tx(conn, stx.hash, projection=['hash']):
        raise ttypes.AppException(code="tx_exist", message="tx already exists in the blockchain")

    if conn.sendtx.find_one({'hash': Binary(stx.hash)}):
        raise ttypes.AppException(code="sending existing")

    if conn.sendtx.find_one({'sequence': stx.sequence}):
        raise ttypes.AppException(code="sequence_exist")
    
    sendtx = {}
    sendtx['hash'] = Binary(stx.hash)
    sendtx['raw'] = Binary(stx.raw)
    sendtx['sent'] = False
    if stx.remoteAddress:
        sendtx['info'] = {'remoteAddress': stx.remoteAddress}
    if stx.sequence:
        sendtx['sequence'] = stx.sequence
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
        if info and info.get('sequence'):
            stx.sequence = info['sequence']
        send_tx_list.append(stx)
    return send_tx_list

# UTXO related
def get_utxo(conn, dtx, output, i):
    utxo = ttypes.UTXO(nettype=get_nettype(conn))
    utxo.address = output['addrs'][0]
    utxo.amountSatoshi = output['v']
    utxo.txid = dtx['hash']
    utxo.vout = i
    utxo.scriptPubKey = output['s']

    b, index = get_tx_db_block(conn, dtx)
    if b:
        tip = get_tip_block(conn)
        utxo.confirmations = tip.height - b['height'] + 1
        utxo.timestamp = b['timestamp']
    else:
        utxo.confirmations = 0
        utxo.timestamp = int(time.mktime(dtx['_id'].generation_time.replace(tzinfo=pytz.utc).utctimetuple()))
        #utxo.timestamp = int(time.time())
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
            if addr in addr_set:
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

def get_related_addrtx_list(conn, addresses, id_order=DESCENDING, cursor=None, count=None):
    q = {'a': {'$in': addresses}}
    if id_order == DESCENDING and cursor:
        q['_id'] = {'$lt': cursor}
    elif id_order == ASCENDING and cursor:
        q['_id'] = {'$gt': cursor}
    qs = conn.addrtx.find(q).batch_size(30).sort([('_id', id_order)])
    if count is not None:
        qs = qs.limit(count)
    return qs

def get_related_db_tx_list_v1(conn, addresses, id_order=DESCENDING, cursor=None, count=None, remove_non_existing_tx=True):
    missing_addrtxs = []
    for at in get_related_addrtx_list(conn, addresses, id_order=id_order,
                                      cursor=None, count=count):
        dtx = get_db_tx(conn, at['t'])
        if not dtx:
            logging.error('No addrtx found %s for address %s', at['t'].encode('hex'), address)
            missing_addrtxs.append(at['_id'])
        if dtx:
            yield dtx

    if remove_non_existing_tx and missing_addrtxs:
        for atid in missing_addrtxs:
            conn.addrtx.remove({'_id': atid})

def get_related_db_tx_list(conn, addresses):
    addr_set = set(addresses)
    arr = conn.tx.find({
        '$or': [
            {'oa': {'$in': addresses}},
            {'ia': {'$in': addresses}}]}).batch_size(30)
    return list(arr)

def get_related_tx_list(conn, addresses):
    arr = get_related_db_tx_list(conn, addresses)
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
        hs = set([])
        ia = set([])
        for input in dtx['vin']:
            h = input.get('hash')
            if h:
                hs.add(h)
            addrs = input.get('addrs')
            if addrs:
                for a in addrs:
                    ia.add(a)
        if ia:
            update['ia'] = list(ia)
            update['vh'] = list(hs)

    if update:    
        #print 'updating addrs', dtx['hash'].encode('hex')
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

def add_dep(conn, dtx):
    '''
    add dependencies 
    '''
    vh = dtx.get('vh')
    if not vh:
        vh = set([])
        for input in dtx['vin']:
            h = input.get('hash')
            if h:
                vh.add(h)
    if vh:
        for h in vh:
            conn.txdep.update({'t': dtx['hash'], 'h': h}, {'$set': {}}, upsert=True)

def remove_dep(conn, dtx):
    '''
    remove tx dependencies when dtx is going to be removed/archived
    '''
    conn.txdep.remove({'t': dtx['hash']})


# new methods
def get_unspent_v1(conn, addresses):
    aset = set(addresses)
    for dtx in get_related_db_tx_list_v1(conn, addresses, id_order=1):
        for i, output in enumerate(dtx['vout']):
            addrs = output.get('addrs')
            if addrs and addrs[0] not in aset:
                continue
            spt = output.get('w', False)
            if not spt:
                utxo = get_utxo(conn, dtx, output, i)
                yield utxo

def get_unspent_v2(conn, addresses, count=200):
    if not addresses:
        return []
    utxos = []
    for addrstat in conn.addrstat.find({'_id': {'$in': addresses}}):
        u = addrstat.get('u', [])
        if len(u) > count:
            u = u[:count]
        for uid in u:
            txid = uid[:32]
            s = uid[33:]
            n = unpack('>I', s)[0]
            dtx = get_db_tx(conn, txid)
            utxo = get_utxo(conn, dtx, dtx['vout'][n], n)
            utxos.append(utxo)
    return utxos
