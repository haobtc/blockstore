namespace js blockstore
namespace py blockstore

/* Enums and exceptions */
enum Network {
  BITCOIN = 1,
  LITECOIN = 2,
  DOGECOIN = 3,
  DARKCOIN = 4  
}

exception AppException {
 1: string code,
 2: string message = ""
}

struct Verification {
  1:bool verified,
  2:string message
}


/* block related */

struct Block {
  1:binary blockHash,
  2:i32 version,
  3:binary prevHash,
  4:binary merkleRoot,
  5:bool isMain,
  6:optional binary nextHash,
  7:i32 cntTxes,
  8:i32 height,
  9:i64 timestamp,
  10:optional binary objId;
}


/* Tx related */
struct TxInput {
  1:binary txid,
  2:i32 vout,
  3:binary script
  4:optional string address,
  5:optional string amountSatoshi,
  6:optional i64 q
}

struct TxOutput {
  1:string address,
  2:string amountSatoshi,
  3:binary script
}

struct Tx {
  1:binary txid,
  2:optional binary blockHash,
  3:optional binary blockIndex,
  4:optional binary objId;
  5:list<TxInput> inputs = [],
  6:list<TxOutput> outputs = []
}

struct TxVerification {
  1:bool verified,
  2:string message
}

/* UTXO related */
struct UTXO {
  1:string address,
  2:string amountSatoshi,
  3:binary txid,
  4:i32 vout
  5:i32 confirmations,
  6:binary scriptPubKey,
  7:i64 timestamp
}

/* Sending TX */
struct SendTx {
  1:binary txid,
  2:binary raw,
  4:optional string remoteAddress
}

/* INV */
enum InvType {
  TX = 1,
  BLOCK = 2
}

struct Inventory {
  1:InvType type,
  2:binary hash
}

service BlockStoreService
{

  /* block related methods */
  Block getBlock(1:Network network, 2:binary blockhash) throws (1:AppException e);
  Block getTipBlock(1:Network network) throws (1:AppException e);
  Verification verifyBlock(1:Network network, 2:Block block);
  void addBlock(1:Network network, 2:Block block) throws (1:AppException e);

  /* tx related methods */	
  Tx getTx(1:Network network, 2:binary txid) throws (1:AppException e);
  list<Tx> getTxList(1:Network network, 2:list<binary> txids);
  list<binary> getMissingTxIdList(1:Network network, 2:list<binary> txids);
  Verification verifyTx(1:Network network, 2:Tx tx);
  void addTxList(1:Network network, 2:list<Tx> txes, 3:bool soft=true);
  list<Tx> getTxListSince(1:Network network, 2:binary objId);
  list<Tx> getLatestTxList(1:Network network);
  list<Tx> getRelatedTxList(1:Network network, 2:list<string> addresses);
  list<binary> getRelatedTxIdList(1:Network network, 2:list<string> addresses);

  /* sendtx related methods */
  list<SendTx> getSendingTxList(1:Network network);
  void sendTx(1:Network network, 2:SendTx sendTx) throws (1:AppException e);

  /* utxo related methods */
  list<UTXO> getUnspent(1:Network network, 2:list<string> addresses);

  /* inv related methods */
  list<Inventory> getMissingInvList(1:Network network, 2:list<Inventory> invs);
}
