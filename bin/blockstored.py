#!/usr/bin/env python
import os
import signal
import getopt, sys

import logging
logging.basicConfig()

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
from thrift.server.TProcessPoolServer import TProcessPoolServer
#from TProcessPoolServer import TProcessPoolServer
from blockstore import BlockStoreService, ttypes
from app.handler import BlockStoreHandler

def setupHandlers():
    signal.signal(signal.SIGINT, handleSIGINT)
    #Optionally if you want to keep the current socket connection open and working
    #tell python to make system calls non-interruptable, which is probably what you want.
    signal.siginterrupt(signal.SIGINT, False)

def handleSIGINT(sig, frame):
     #clean up state or what ever is necessary
     sys.exit(0)

pgid = os.getpgid(0)

def assign_pgid():
    gid = os.getpgid(0)
    print os.getpid(), gid
    
def run(host='localhost', port=19090):
    handler = BlockStoreHandler()
    processor = BlockStoreService.Processor(handler)
    transport = TSocket.TServerSocket(host=host, port=port)
    tfactory = TTransport.TBufferedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()

    #server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)
    server = TProcessPoolServer(processor, transport, tfactory, pfactory)
    server.setNumWorkers(4)
    server.setPostForkCallback(assign_pgid)
    #server.setPostForkCallback(setupHandlers)
    server.serve()


def usage():
    print 'blockstored: thrift server for block db of bitcoin, litecoin and dogecoin'
    print 'Usage: %s [opts]' % sys.argv[0]
    print ' -h|--host <host> server host, default = "localhost"'
    print ' -p|--port <port> server port, default = 19090'
    print ' -u               print this message'
    
def main():
    # parse arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h:p:u', ['host=', 'port=', 'usage'])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)
    
    kwargs = {}
    for o, a in opts:
        if o == '-h':
            kwargs['host'] = a
        elif o == '-p':
            kwargs['port'] = int(a)
        elif o == '-u':
            usage()
            sys.exit(0)
    run(**kwargs)

if __name__ == '__main__':
    main()
