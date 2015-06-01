import logging
from bson.binary import Binary
import database
from blockstore import BlockStoreService, ttypes
from helper import resolve_network

from tx import get_tx, get_tx_list, get_missing_txid_list, verify_tx_mempool, verify_tx_chain
from tx import get_sending_tx_list, get_send_tx_list, send_tx, get_tail_tx_list, get_tx_list_since
from tx import get_unspent, get_related_txid_list, get_related_tx_list, remove_tx
from tx import save_tx, update_addrs

from block import get_block, get_block_at_height,  get_tip_block, verify_block, get_missing_block_hash_list, add_block
from block import get_tail_block_list, rewind_tip, link_txes
from misc import set_peers, get_peers, itercol, push_peers, pop_peers

def network_conn(nettype):
    netname = resolve_network(nettype)
    conn = database.conn(netname)
    conn.nettype = nettype
    return conn    
    
class BlockStoreHandler:
    def getBlock(self, nettype, blockhash):
        conn = network_conn(nettype)
        block = get_block(conn, blockhash)
        if not block:
            raise ttypes.NotFound();
        return block

    def getBlockAtHeight(self, nettype, height):
        conn = network_conn(nettype)
        block = get_block_at_height(conn, height)
        if not block:
            raise ttypes.NotFound();
        return block

    def getTipBlock(self, nettype):
        conn = network_conn(nettype)
        block = get_tip_block(conn)
        if not block:
            raise ttypes.NotFound();
        return block

    def getTailBlockList(self, nettype, n):
        conn = network_conn(nettype)
        return get_tail_block_list(conn, n)

    def verifyBlock(self, nettype, block):
        conn = network_conn(nettype)
        r = verify_block(conn, block)
        return ttypes.Verification(verified=r[0], message=r[1])

    def addBlock(self, nettype, block, txids):
        conn = network_conn(nettype)
        with database.transaction(conn, isolation='serializable') as conn:
            add_block(conn, block, txids)

    def linkBlock(self, nettype, blockhash, txids):
        conn = network_conn(nettype)
        with database.transaction(conn, isolation='serializable') as conn:
            block = get_block(conn, blockhash)
            if not block:
                raise ttypes.NotFound()
            link_txes(conn, block, txids)

    def rewindTip(self, nettype, height):
        conn = network_conn(nettype)
        with database.transaction(conn) as conn:
            v, m = rewind_tip(conn, height)
            if not v:
                raise ttypes.AppException(code='rewind_failed', message=m)
            
    def getTx(self, nettype, txid):
        conn = network_conn(nettype)
        dtx = get_tx(conn, txid)
        if not dtx:
            raise ttypes.NotFound()
        return dtx

    def getTxList(self, nettype, txids):
        conn = network_conn(nettype)
        return get_tx_list(conn, txids, keep_order=True)

    def getTxListSince(self, nettype, since, n):
        conn = network_conn(nettype)
        return get_tx_list_since(conn, since, n)

    def getTailTxList(self, nettype, n):
        conn = network_conn(nettype)
        return get_tail_tx_list(conn, n)

    def getRelatedTxIdList(self, nettype, addresses):
        conn = network_conn(nettype)
        return get_related_txid_list(conn, addresses)

    def getRelatedTxList(self, nettype, addresses):
        conn = network_conn(nettype)
        return get_related_tx_list(conn, addresses)

    def getUnspent(self, nettype, addresses):
        conn = network_conn(nettype)
        return get_unspent(conn, addresses)

    def getMissingTxIdList(self, nettype, txids):
        conn = network_conn(nettype)
        return get_missing_txid_list(conn, txids)

    def addTxList(self, nettype, txes, mempool):
        conn = network_conn(nettype)
        with database.transaction(conn) as conn:
            verified_txes = []
            for tx in txes:
                print 'saving', tx.hash.encode('hex')
                if mempool:
                    v, m = verify_tx_mempool(conn, tx)
                else:
                    v, m = verify_tx_chain(conn, tx)
                if v:
                    verified_txes.append(tx)
                    save_tx(conn, tx)
                else:
                    logging.warn('verify tx failed %s, message=%s',
                                 tx.hash.encode('hex'), m)

        for dtx in itercol(conn, conn.tx, 
                           'update_addrs.tx._id',
                           len(verified_txes)):
            update_addrs(conn, dtx)

    def removeTx(self, nettype, txid):
        conn = network_conn(nettype)
        tx = get_tx(conn, txid)
        if not tx:
            raise ttypes.NotFound()
        with database.transaction(conn) as conn:
            return remove_tx(conn, tx)

    def verifyTx(self, nettype, tx, mempool):
        conn = network_conn(nettype)
        if mempool:
            r = verify_tx_mempool(conn, tx)
        else:
            r = verify_tx_chain(conn, tx)
        return ttypes.Verification(verified=r[0], message=r[1])

    def getSendingTxList(self, nettype):
        conn = network_conn(nettype)
        return get_sending_tx_list(conn)

    def getSendTxList(self, nettype, txids):
        conn = network_conn(nettype)
        return get_send_tx_list(conn, txids)

    def sendTx(self, nettype, stx):
        conn = network_conn(nettype)
        return send_tx(conn, stx)

    def getMissingInvList(self, nettype, invs):
        conn = network_conn(nettype)
        txids = [inv.hash for inv in invs if inv.type == ttypes.InvType.TX]
        block_hashes = [inv.hash for inv in invs if inv.type == ttypes.InvType.BLOCK]
        missing_invs = []
        for txid in get_missing_txid_list(conn, txids):
            inv = ttypes.Inventory(type=ttypes.InvType.TX, hash=txid)
            missing_invs.append(inv)
        for bhash in get_missing_block_hash_list(conn, block_hashes):
            inv = ttypes.Inventory(type=ttypes.InvType.BLOCK, hash=bhash)
            missing_invs.append(inv)
        return missing_invs

    def getPeers(self, nettype):
        conn = network_conn(nettype)
        return get_peers(conn)

    def setPeers(self, nettype, peers):
        conn = network_conn(nettype)
        return set_peers(conn, peers)

    def pushPeers(self, nettype, peers):
        conn = network_conn(nettype)
        return push_peers(conn, peers)

    def popPeers(self, nettype, n):
        conn = network_conn(nettype)
        return pop_peers(conn, n)
