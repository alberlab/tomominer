import time
import sys
import random

import logging


def sleep(s, f, q):
  logging.debug("sleep time = %s, exc_rate = %s, crash_rate = %s", s, f, q)
  time.sleep(s)
  if random.random() < f:
    logging.warning("This run of task is going to raise an exception!")
    raise RuntimeError()
  if random.random() < q:
    logging.warning("This run of task is going to 'crash'!")
    sys.exit()
  return True
