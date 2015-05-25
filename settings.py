db_conn = 'mongodb://localhost:27017'

try:
    from local_settings import *
except ImportError:
    pass
