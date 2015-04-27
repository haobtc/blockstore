import pytz
from datetime import datetime
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

def utc_now():
    return datetime.utcnow().replace(tzinfo=pytz.utc)

def generated_seconds(gtime):
    d = utc_now() - gtime
    return d.days * 86400 + d.seconds
