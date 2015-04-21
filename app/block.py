from blockstore import BlockStoreService, ttypes
from bson.binary import Binary
from bson.objectid import ObjectId
import database

def db2t_block(conn, block):
    b = ttypes.Block()
    b.blockHash = block['hash']
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
    return b

def t2db_block(b):
    block = {}
    block['hash'] = b.blockHash
    block['version'] = b.version
    block['prev_hash'] = b.prevHash
    block['cntTxes'] = b.cntTxes
    block['height'] = b.height
    block['merkleRoot'] = b.merkelRoot
    block['timestmap'] = b.timestamp
    block['isMain'] = b.isMain
    if b.nextHash:
        block['next_hash'] = b.nextHash
        
    if b.objId:
        block['_id'] = ObjectId(b.objId)
    return block
    

def get_block(conn, blockhash):
    b =  conn.block.find_one({'hash': Binary(blockhash)})
    if b:
        return db2t_block(conn, b)

def get_tip_block(conn):
    tip = conn.var.find_one({'key': 'tip'})
    if tip:
        return get_block(conn, tip['blockHash'])

def verify_block(conn, tblock):
    b = get_block(conn, tblock.blockHash)
    if b:
        return False, 'already_exist'
    pb = get_block(conn, tblock.prevHash)
    if not pb:
        return False, 'prev_not_exist'

    tip_block = get_tip_block(conn)
    if tip_block and pb.height < tip_block.height - 8:
        return False, 'prev_too_old'
        
    return True, 'ok'

def set_block_main(conn, tblock, isMain):
    tblock.isMain = isMain
    conn.block.update({'hash': Binary(tblock.blockHash)}, {'$set': {'isMain': isMain}})

def add_block(conn, new_tip):
    '''
    Insert the block in the blockchain
    '''
    v, m = verify_block(conn, new_tip)
    if not v:
        raise ttypes.AppException(code=m)
    
    old_tip = get_tip_block(conn)
    if not old_tip:
        # genesis block
        set_tip_block(conn, new_tip)
        return
    
    new_prev = get_block(conn, new_tip.prevHash)
    old_next = get_block(conn, new_prev.nextHash)

    if new_prev.isMain:
        # Orphan old_tip -> new_prev
        p = old_tip
        while p.blockHash != new_prev.blockHash:
            set_block_main(conn, p, False)
            p = get_block(conn, p.prevHash)
        p.nextHash = new_tip
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
        while p.blockHash != base_p.blockHash:
            set_block_main(conn, p, False)
            p = get_block(conn, p.prevHash)
        p.nextHash = last_p

    save_block(conn, p)
    set_tip_block(conn, new_tip)

def save_block(conn, b):
    db_block = t2db_block(b)
    conn.block.save(db_block)

def set_tip_block(conn, new_tip):
    set_block_main(conn, new_tip)
    conn.var.update({'key': 'tip'}, {'$set': {'blockHash': new_tip.blockHash}})            

def get_missing_block_hash_list(conn, bhashes):
    if not bhashes:
        return []
    binary_bhash_list = [Binary(bhash) for bhash in bhashes]
    hash_set = set(binary_bhash_list)
    found_set = set(b['hash']
                    for b in conn.block.find({'hash': {'$in': binary_bhash_list}},
                                             projection=['hash']))
    return list(hash_set - found_set)
