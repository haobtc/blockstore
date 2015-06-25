from bsd.database import conn

def ensure_indices(c):
    c.block.ensure_index('hash', unique=True)
    c.block.ensure_index('prev_hash')
    c.block.ensure_index([('height', -1)])

    c.tx.ensure_index('hash', unique=True)
    c.tx.ensure_index('oa')
    c.tx.ensure_index('ia')
    c.tx.ensure_index('vh')

    c.txblock.ensure_index([('t', 1), ('b', 1)], unique=True)
    c.txblock.ensure_index('t')
    c.txblock.ensure_index('b')
    c.txblock.ensure_index([('t', 1), ('i', 1)])
    #c.tx.ensure_index('vin.hash')
    
    #nc.tx.ensure_index([('vin.hash', 1), ('vin.n', 1)])
    #c.tx.ensure_index('vin.k')
    #c.tx.ensure_index('vin.addrs')
    #c.tx.ensure_index('vout.addrs')
    #c.tx.ensure_index('vout.w')

    c.addrtx.ensure_index([('a', 1), ('_id', -1)])
    c.addrtx.ensure_index([('a', 1), ('t', 1)], unique=True)

    c.txdep.ensure_index('h')
    c.txdep.ensure_index('t')

    c.watchedaddr.ensure_index([('a', 1), ('g', 1)], unique=True)
    c.watchedaddrtx.ensure_index([('a', 1), ('_id', 1)])
    c.watchedaddrtx.ensure_index([('a', 1), ('t', 1)], unique=True)
    c.watchedaddrtx.ensure_index('t')

    c.var.ensure_index('key', unique=True)
    c.sendtx.ensure_index('hash',  unique=True)
    c.sendtx.ensure_index('sequence',  unique=True, sparse=True)
    c.peerpool.ensure_index([('host', 1), ('port', 1)], unique=True)
    c.peerpool.ensure_index([('borrowed', -1)])
    c.peerpool.ensure_index([('borrowed', -1), ('lastSeen', -1)])
    c.peerpool.ensure_index([('borrowed', -1), ('version', -1), ('lastSeen', -1)])
    c.peerpool.ensure_index([('borrowed', -1), ('lastBorrowed', -1)])
    

def main():
    for netname in ['bitcoin', 'dogecoin', 'litecoin', 'darkcoin']:
        c = conn(netname)
        ensure_indices(c)

if __name__ == '__main__':
    main()
