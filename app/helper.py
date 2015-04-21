from blockstore import BlockStoreService, ttypes
from bson.binary import Binary

def resolve_network(netname):
    if netname == ttypes.Network.BITCOIN:
        return 'bitcoin'
    elif netname == ttypes.Network.LITECOIN:
        return 'litecoin'
    elif netname == ttypes.Network.DOGECOIN:
        return 'dogecoin'
    elif netname == ttypes.Network.DARKCOIN:
        return 'darkcoin'

