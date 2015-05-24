db_conn = 'mongodb://localhost:27017'
stats_db_path = '/data/blockstore/stats.%s.leveldb'

try:
    from local_settings import *
except ImportError:
    pass
