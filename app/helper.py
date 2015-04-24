from blockstore import BlockStoreService, ttypes
from bson.binary import Binary

def resolve_network(nettype):
    if nettype == ttypes.Network.BITCOIN:
        return 'bitcoin'
    elif nettype == ttypes.Network.LITECOIN:
        return 'litecoin'
    elif nettype == ttypes.Network.DOGECOIN:
        return 'dogecoin'
    elif nettype == ttypes.Network.DARKCOIN:
        return 'darkcoin'

