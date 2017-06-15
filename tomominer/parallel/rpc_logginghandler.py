import logging

class RPCLoggingHandler(logging.Handler):
  """
  A logging handler to send logging messages to a centralized server which
  writes all data to a central log file.
  """

  def __init__(self, rpc):
    """
    Initialise an instance, using the passed queue.

    :param rpc The server object we will send messages to using rpc.log(record)
    """
    logging.Handler.__init__(self)
    self.rpc = rpc

  def emit(self, record):
    """
    Emit a record.

    Writes the LogRecord to the remote rpc server

    :param record a logging record.
    """
    try:
      ei = record.exc_info
      if ei:
        dummy = self.format(record) # just to get traceback text into record.exc_text
        record.exc_info = None  # not needed any more
      self.rpc.log(record)
    except (KeyboardInterrupt, SystemExit):
      raise
    except:
      self.handleError(record)


