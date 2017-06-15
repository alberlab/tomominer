
from rpc_server   import RPCServer
from queue_server import QueueServer

class Server(RPCServer, QueueServer):

  def __init__(self, addr, timeout_thread_interval=30, get_task_timeout=30):
    QueueServer.__init__(self, timeout_thread_interval, get_task_timeout) #, self)
    RPCServer.__init__(self, addr)
