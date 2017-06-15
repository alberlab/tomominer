#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import pickle
import time
import logging

class RPCClient(object):
  """
  A client which communicates with a RPCServer instance.

  This client creates a connection to the server over which all communication
  will take place.  Any call made to this object will be forwarded as a
  request to the server.

  client = RPCClient('localhost', 5000)

  client.func(1,2,y=3)

  will send this pickled message to the server:

    ('func', (1,2), {y:3})

  where the fields are the remote function name, the arguments, and keyword
  arguments.

  The client will then block waiting for a response from the server.  The
  response will be a tuple with either the result or the exception that was
  raised.

  ('OK', result)
  ('ERR', exc)

  If the message is OK, the result is returned.  Otherwise the exception is
  raised and propogated to the caller of client.func().
  """

  def __init__(self, host, port, delay=10, max_tries=12, tcp_keepidle=60*5, tcp_keepintvl=30, tcp_keepcnt=5):
    """
    Open a connection to the server object.

    :param host: Host to connect to.
    :type  host: str
    :param port: Port to connect to of host.
    :type  port: int
    :param delay: How many seconds to sleep between connection attempts on an error.
    :param max_tries: The number of times to try and connect.  With a 5 second delay per attempt.  By default None, which is infinite retries.
    :param tcp_keepidle: Number of seconds to wait before initiating keep-alive probes.
    :param tcp_keepintvl: Number of seconds between keep-alive probes.
    :param tcp_keepcnt: Number of tries sending keep-alive probes without a response, before we give up and quit.
    """
    self.host = host
    self.port = port

    self.delay    = delay
    self.max_tries  = max_tries

    self.tcp_keepidle  = tcp_keepidle
    self.tcp_keepintvl = tcp_keepintvl
    self.tcp_keepcnt   = tcp_keepcnt

    self._connect()


  def __del__(self):
    """
    On delete cleanup the open socket.
    """
    self._close()


  def _connect(self):
    """
    Create a connection to the server.

    We turn on the keepalive TCP options for the socket.  This will allow
    us to detect failures in the socket connections faster.
    """

    # number of connection attempts.
    n_tries = 0

    while True:
      # create a new TCP socket.
      # Socket must be non-blocking for makefile below.  Do not settimeout().
      self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

      # Turn on TCP keepalive.
      self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
      # This next part is non-portable! These are the linux flags.
      self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,  self.tcp_keepidle)
      self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT,   self.tcp_keepcnt)
      self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, self.tcp_keepintvl)

      # try to connect.
      try:
        self.socket.connect((self.host, self.port))
        self.rfile = self.socket.makefile('rb')
        self.wfile = self.socket.makefile('wb')
        return
      except Exception, exc:
        logging.error("exception when connecting to server: %s", exc)
        # close just in case.
        try:
          self.socket.shutdown(socket.SHUT_RDWR)
          self.socket.close()
        except Exception, exc2:
          logging.error("exception when shutting down socket: %s", exc2)
          pass
        # failed to connect to host.  
        # If we have exceeded our max attempts, raise the exception.  Otherwise try again.
        n_tries += 1
        logging.error("socket connection error: Attempt %s of %s failed.", n_tries, self.max_tries)
        if n_tries >= self.max_tries:
          raise exc
        logging.error("socket connection error: Will re-try in %s sec.", self.delay)
        time.sleep(self.delay)
        continue

  def _close(self):
    """
    Shutdown the connection to the server.  Clean up the current socket.
    """
    self.socket.shutdown(socket.SHUT_RDWR)
    self.socket.close()
    self.rfile.close()
    self.wfile.close()

  def __getattr__(self, name):
    """
    This remaps all attributes over the network to the server object.
    Calling any local attribute with run the resulting function on the
    remote system.
    """
    def proxy(*args, **kwargs):

      while True:

        try:
          pickle.dump((name, args, kwargs), self.wfile, protocol=2)
          self.wfile.flush() # to make sure the server won't wait forever
          status, result = pickle.load(self.rfile)
          if status == 'OK':
            return result
          else:
            raise result
        except socket.timeout:
          # timeouts are fine.  Just continue
          time.sleep(5.0)
          continue
        except (socket.error, EOFError) as e:
          # Any other socket error is a problem.
          # Try to close the old socket and open a new one.
          #
          # Most likely the socket error will manifest as a broken
          # connection and an EOF Error raised by the pickle.loads()
          # command.
          try:
            self._close()
          except:
            pass
          self._connect()

    return proxy

if __name__ == '__main__':

  host = "localhost"
  port = 8000

  rpcclient = RPCClient(host, port)

  rpcclient.echo('Hello world!')
  rpcclient.div(42, 2)
  rpcclient.is_computer_on()
  rpcclient.div(divisor=2, dividend=42)
  try:
    rpcclient.raising_function(False)
    print "No exception thrown!"
  except Exception as ex:
    pass
  try:
    rpcclient._private(x=2)
  except Exception as ex:
    pass

  rpcclient._close()
  del rpcclient
