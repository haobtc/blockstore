from app.database import conn

def ensure_indices(c):
    c.block.ensure_index('hash', unique=True)
    c.block.ensure_index([('height', -1)])
  
    #c.tx.ensure_index('hash', unique=True)
    #c.tx.ensure_index('bhs')
    #nc.tx.ensure_index([('vin.hash', 1), ('vin.n', 1)])
    #c.tx.ensure_index('vin.k')
    #c.tx.ensure_index('vin.addrs')
    c.tx.ensure_index('vout.addrs')
    #c.tx.ensure_index('vout.w')

    c.var.ensure_index('key', unique=True)
    c.sendtx.ensure_index('hash',  unique=True)

def main():
    for netname in ['bitcoin', 'dogecoin', 'darkcoin']:
        c = conn(netname)
        ensure_indices(c)

if __name__ == '__main__':
    main()
