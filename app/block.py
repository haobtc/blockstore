from blockstore import BlockStoreService, ttypes
from pymongo import DESCENDING, ASCENDING
from bson.binary import Binary
from bson.objectid import ObjectId
from misc import get_var, set_var, clear_var
from helper import generated_seconds
import database

def db2t_block(conn, block):
    b = ttypes.Block(nettype=conn.nettype)
    b.hash = block['hash']
    b.version = block['version']
    b.prevHash = block['prev_hash']
    b.cntTxes = block['cntTxes']
    b.height = block['height']
    b.merkleRoot = block['merkle_root']
    b.timestamp = block['timestamp']
    b.isMain = block['isMain']
    
    if block.get('next_hash'):
        b.nextHash = block['next_hash']
    if block.get('_id'):
        b.objId = block['_id'].binary
    if block.get('bits'):
        b.bits = block['bits']
    return b

def t2db_block(b):
    block = {}
    block['hash'] = Binary(b.hash)
    block['version'] = b.version
    block['prev_hash'] = Binary(b.prevHash)
    block['cntTxes'] = b.cntTxes
    block['height'] = b.height or 0
    block['merkle_root'] = Binary(b.merkleRoot)
    block['timestamp'] = b.timestamp
    block['isMain'] = b.isMain
    if b.nextHash:
        block['next_hash'] = Binary(b.nextHash)
        
    if b.objId:
        block['_id'] = ObjectId(b.objId)

    if b.bits is not None:
        block['bits'] = b.bits
    return block
    

def get_block(conn, blockhash):
    if blockhash is None:
        return
    b =  conn.block.find_one({'hash': Binary(blockhash)})
    if b:
        return db2t_block(conn, b)

def get_tip_block(conn):
    v = get_var(conn, 'tip')
    if v:
        return get_block(conn, v['blockHash'])

def verify_block(conn, tblock):
    b = get_block(conn, tblock.hash)
    if b:
        return False, 'already_exist'
    tip_block = get_tip_block(conn)
    if tip_block:
        pb = get_block(conn, tblock.prevHash)
        if not pb:
            return False, 'prev_not_exist'

        if pb.height < tip_block.height - 8:
            return False, 'prev_too_old'
        
    return True, 'ok'

def set_block_main(conn, tblock, isMain):
    tblock.isMain = isMain
    conn.block.update({'hash': Binary(tblock.hash)}, {'$set': {'isMain': isMain}})

def add_block(conn, new_tip, txids):
    '''
    Insert the block in the blockchain
    '''
    v, m = verify_block(conn, new_tip)
    if not v:
        raise ttypes.AppException(code='verify_failed', message=m)
    
    old_tip = get_tip_block(conn)
    if not old_tip:
        # genesis block
        new_tip.height = 0
        print 'save tip block', new_tip
        set_tip_block(conn, new_tip)
        link_txes(conn, new_tip, txids)
        return
    
    new_prev = get_block(conn, new_tip.prevHash)
    new_tip.height = new_prev.height + 1
    old_next = get_block(conn, new_prev.nextHash)

    if new_prev.isMain:
        # Orphan old_tip -> new_prev
        p = old_tip
        while p.hash != new_prev.hash:
            set_block_main(conn, p, False)
            p = get_block(conn, p.prevHash)
        p.nextHash = new_tip.hash
    else:
        # Unorphan new_prev until is Main
        p = new_prev
        last_p = p
        while not p.isMain:
            set_block_main(conn, p, True)
            last_p = p
            p = get_block(conn, p.prevHash)
        # Orphan old_tip to p
        base_p = p
        p = old_tip
        while p.hash != base_p.hash:
            set_block_main(conn, p, False)
            p = get_block(conn, p.prevHash)
        p.nextHash = last_p.hash
    save_block(conn, p)

    set_tip_block(conn, new_tip)
    link_txes(conn, new_tip, txids)


def link_txes(conn, block, txids):
    'link txes with this block'
    for i, txid in enumerate(txids):
        conn.tx.update({'hash': Binary(txid)}, {'$push': {'bhs': Binary(block.hash), 'bis': i}})

def save_block(conn, b):
    db_block = t2db_block(b)
    db_block.pop('_id', None)
    conn.block.update({'hash': db_block['hash']}, {'$set': db_block}, upsert=True)

def set_tip_block(conn, new_tip):
    if new_tip:
        new_tip.isMain = True
        save_block(conn, new_tip)
        set_var(conn, 'tip', blockHash=Binary(new_tip.hash))
    else:
        clear_var(conn, 'tip')

def get_missing_block_hash_list(conn, bhashes):
    if not bhashes:
        return []
    binary_bhash_list = [Binary(bhash) for bhash in bhashes]
    hash_set = set(binary_bhash_list)
    found_set = set(b['hash']
                    for b in conn.block.find({'hash': {'$in': binary_bhash_list}},
                                             projection=['hash']))
    return list(hash_set - found_set)

def get_tail_block_list(conn, n):
    n = min(n, 10)
    arr = conn.block.find({'isMain': True}).sort([('height', DESCENDING)]).limit(n)
    arr = list(arr)
    arr.reverse()
    return [db2t_block(conn, b) for b in arr]

def remove_block(conn, bhash, remove_txes=True):
    binary_phash = Binary(bhash)

    arr = list(conn.block.find({'prev_hash': binary_phash}))
    for b in arr:
        remove_block(conn, b['hash'])

    # unlink txes with this 
    for dtx in conn.tx.find({'bhs': binary_phash}):
        new_bhs = []
        new_bis = []
        for h, i in zip(dtx['bhs'], dtx['bis']):
            if h != binary_phash:
                new_bhs.append(h)
                new_bis.append(i)
        dtx['bhs'] = new_bhs
        dtx['bis'] = new_bis
        conn.tx.update({'hash': dtx['hash']},
                       {'$set': {'bhs': new_bhs, 'bis': new_bis}})
        if (not new_bhs
            and generated_seconds(dtx['_id'].generation_time) > 10
            and remove_txes):
            from tx import remove_db_tx
            remove_db_tx(conn, dtx)

    # remove the block its self
    conn.block.remove({'hash': binary_phash})
    
def rewind_tip(conn, height):
    tip = get_tip_block(conn)
    if not tip:
        return False, 'no tip block'
    print 'current tip height is', tip.height
    if tip.height <= height:
        return False, 'height >= tip'

    p = tip
    while p and p.height > height:
        prev = get_block(conn, p.prevHash)
            
        remove_block(conn, p.hash)
        set_tip_block(conn, prev)
        p = prev
    return True, 'ok'
            
