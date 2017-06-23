#!/usr/bin/python
# -*- coding: utf-8 -*-

import SocketServer
import pickle
import threading
import logging

# Figure out how to pass in connection/worker information to handler, and pass
# to server.  Or have the _dispatch intercept proto_* methods and call them on
# the server.  Then the RPCServer can get that information from the worker if
# they send that message first.

# TODO: This should be rewritten using Tornado or something similar.

class RPCHandler(SocketServer.StreamRequestHandler):
  """
  Connection object that communicates with a RPCClient object.
  """

  def handle(self):
    """
    Connect to the socket and send pickled request/response across until
    the connection is closed.

    Within the connection, we enter a loop loading pickled data, processing
    it and returning results.
    """
    self.server.increment_active_connections()
    while True:

      try:
        data = pickle.load(self.rfile)
      except EOFError:
        # EOF means we're done with this request.
        break
      try:
        result = self.server._dispatch(data)
      except Exception, e:
        pickle.dump(('ERR', e), self.wfile, protocol=2)
      else:
        pickle.dump(('OK', result), self.wfile, protocol=2)

    self.server.decrement_active_connections()

class RPCServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
  """
  The actual server itself.  This is the TCP server which creates a new
  thread for every connection.

  MixIn style class for the server.  This adds the capability for registering
  an object that supplies the methods that are looked up.  It also supplies
  the dispatch function for calling the mapped method.
  """
  daemon_threads    = True
  allow_reuse_address = True
  SocketServer.TCPServer.allow_reuse_address = True
  active_connections  = 0

  def __init__(self, addr, requestHandler=RPCHandler, bind_and_activate=True, instance=None):
    if not instance:
      self.instance = self
    else:
      self.instance = instance
    self.active_connections_lock = threading.Lock()

    SocketServer.TCPServer.__init__(self, addr, requestHandler, bind_and_activate)

  def increment_active_connections(self):
    with self.active_connections_lock:
      self.active_connections += 1

  def decrement_active_connections(self):
    with self.active_connections_lock:
      self.active_connections -= 1

  def register_instance(self, obj):
    """
    Register an object which will provides the functions to be called remotely.

    :param obj:  the object that supplies all of the methods that will be
          called remotely.
    """
    self.instance = obj

#   def proto_register_worker():
#     """
#     No way to associate a worker with a handler.  We want to track how many
#     of each type of connections have been made.
#     """
#     pass

  def _dispatch(self, data):
    """
    Run a requested function on provided arguments.  Each request contains
    a function name, arguments, and keyword arguments.  The function name
    must match a method of the registered instance class.  It must also not
    start with underscores, as an attempt to protect private methods.

    :param data: The request to process.
    """

    try:
      method, args, kwargs = data
    except:
      raise
    # special case shutdown call.
    if method == 'shutdown':
      log.info("Shutdown called.  Server is exiting")
      exit()


    if self.instance is None:
      raise Exception("No instance installed on the server.")

    if method.startswith("_"):
      raise AttributeError("Cannot call methods with leading '_'")
#     elif method.startswith("proto_") and hasattr(self, method):
#       func = getattr(self, method)
#       if not callable(func):
#         raise AttributeError("Requested function (%s) is not callable" % (method,))
#       return func(*args, **kwargs)
    elif hasattr(self.instance, method):
      func = getattr(self.instance, method)
      if not callable(func):
        raise AttributeError("Requested function (%s) is not callable" % (method,))
      return func(*args, **kwargs)
    else:
      raise AttributeError("Requested function (%s) not found in instance", (method))


if __name__ == '__main__':

  host = "localhost"
  port = 8000

  class Test(object):
    def echo(self, data):
      '''Method for returning data got from client'''
      return data

    def div(self, dividend, divisor):
      '''Method to divide 2 numbers'''
      return dividend/divisor

    def is_computer_on(self):
      return True

    def raising_function(self, arg):
      if not arg:
        raise Exception

    def _private_fn(self, x):
      return x + 3

  server = RPCServer((host, port), RPCHandler)
  server.register_instance(Test())

  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print 'Exiting...'
    server.server_close()
