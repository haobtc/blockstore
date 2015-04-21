from blockstore import BlockStoreService, ttypes
from bson.binary import Binary
import database
from helper import resolve_network
from tx import get_tx, get_tx_list, get_missing_txid_list, verify_tx
from tx import get_sending_tx_list, send_tx, get_latest_tx_list, get_tx_list_since
from tx import get_unspent, get_related_txid_list, get_related_tx_list
from block import get_block, get_tip_block, verify_block, get_missing_block_hash_list


def network_conn(netname):
    netname = resolve_network(netname)
    return database.conn(netname)
    
class BlockStoreHandler:
    def getBlock(self, netname, blockhash):
        conn = network_conn(netname)
        block = get_block(conn, blockhash)
        if not block:
            raise ttypes.AppException(code='not_found')
        return block

    def getTipBlock(self, netname):
        conn = network_conn(netname)
        block = get_tip_block(conn)
        if not block:
            raise ttypes.AppException(code='not_found')
        return block

    def verifyBlock(self, netname, block):
        conn = network_conn(netname)
        r = verify_block(conn, block)
        return ttypes.Verification(verified=r[0], message=r[1])

    def addBlock(self, netname, block):
        conn = network_conn(netname)
        with database.transaction(conn) as conn:
            add_block(conn, block)

    def getTx(self, netname, txid):
        conn = network_conn(netname)
        dtx = get_tx(conn, txid)
        if not dtx:
            raise ttypes.AppException(code='not_found')
        return dtx

    def getTxList(self, netname, txids):
        conn = network_conn(netname)
        return get_tx_list(conn, txids)

    def getTxListSince(self, netname, since):
        conn = network_conn(netname)
        return get_tx_list_since(conn, since)

    def getLatestTxList(self, netname):
        conn = network_conn(netname)
        return get_latest_tx_list(conn)


    def getRelatedTxIdList(self, netname, addresses):
        conn = network_conn(netname)
        return get_related_txid_list(conn, addresses)

    def getRelatedTxList(self, netname, addresses):
        conn = network_conn(netname)
        return get_related_tx_list(conn, addresses)

    def getUnspent(self, netname, addresses):
        conn = network_conn(netname)
        return get_unspent(conn, addresses)

    def getMissingTxIdList(self, netname, txids):
        conn = network_conn(netname)
        return get_missing_txid_list(conn, txids)

    def addTxList(self, netname, txes, soft=True):
        conn = network_conn(netname)
        verifided_txes = []
        for tx in txes:
            v, m = verify_tx(conn, netname, soft=soft)
            if v:
                verified_txes.append(tx)

        for tx in verified_txes:
            save_tx(conn, tx)

    def verifyTx(self, netname, tx):
        conn = network_conn(netname)
        r = verify_tx(conn, tx)
        return ttypes.Verification(verified=r[0], message=r[1])

    def getSendingTxList(self, netname):
        conn = network_conn(netname)
        return get_sending_tx_list(conn)

    def sendTx(self, netname, stx):
        conn = network_conn(netname)
        return send_tx(conn, stx)

    def getMissingInvList(self, netname, invs):
        conn = network_conn(netname)
        txids = [inv.hash for inv in invs if inv.type == ttypes.InvType.TX]
        block_hashes = [inv.hash for inv in invs if inv.type == ttypes.InvType.BLOCK]
        missing_invs = []
        for txid in get_missing_txid_list(conn, txids):
            inv = ttypes.Inventory(type=ttypes.InvType.TX, hash=txid)
            missing_invs.append(inv)
        print block_hashes
        for bhash in get_missing_block_hash_list(conn, block_hashes):
            inv = ttypes.Inventory(type=ttypes.InvType.BLOCK, hash=bhash)
            missing_invs.append(inv)
        return missing_invs
