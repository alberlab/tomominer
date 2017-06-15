import sys
import random

from collections import OrderedDict
import functools
import logging

class LRUCache:
  """
  LRU Cache (Least Recently Used)

  This cache discards data according to when it was accessed last.  When
  limits are hit (size/count) it discards elements that have been used least
  recently.
  """

  def __init__(self, max_size=None, max_count=None, size_fn=sys.getsizeof):
    """
    Create the cache, and place limits.

    :param max_size: maximum size in bytes of the storage to be used.
    :param max_count: maximum number of objects to be cached
    :param size_fn: the function to be used to calculate the size of cached objects.

    The size parameter is only useful in the case that you provide the
    size_fn definition. For any complex objects the builtin getsizeof()
    will fail.
    """

    self.od = OrderedDict()

    if max_size is None:
      self.max_size = float('inf')
    else:
      self.max_size  = max_size
    if max_count is None:
      self.max_count = float('inf')
    else:
      self.max_count = max_count

    self.size  = 0

    self.size_fn = size_fn

  def __getitem__(self, key):
    """
    When an item is accessed from the cache, we update its use history.
    Here we delete/re-insert as the easiest way to update its usage.
    """

    value = self.od.pop(key)
    # reinsert the key/value pair since it has been used.
    self.od[key] = value
    return value

  def __setitem__(self, key, value):
    """
    Insert a key/value
    """

    # remove if already in cache (overwriting does not update position)
    if key in self.od:
      old_value = self.od.pop(key)
      self.size -= self.size_fn(old_value)

    # reinsert the element.
    self.od[key] = value
    self.size += self.size_fn(value)

    # apply cache limits.  Drop elements until we are back in compliance.
    while len(self.od) >= self.max_count or self.size >= self.max_size:
      # popitem(False) for FIFO
      k,v = self.od.popitem(last=False)
      self.size -= self.size_fn(v)

  def __contains__(self, key):
    return key in self.od


def lru_memoize(cache=LRUCache()):
  """
  A memoization decorator.

  This will use the arguments of a function call as
  a key, and will use a simple lookup table instead of function calls when
  the result has already been computed, and if the result is stored in the
  given cache.

  :param cache: The cache to use for key/value storage of function parameters
  and function results.
  """

  def decorating_function(user_function):

    @functools.wraps(user_function)
    def wrapper(*args, **kwargs):
      key = args + tuple(sorted(kwargs.items()))

      if key in cache:
        wrapper.hits += 1
        value = cache[key]
        logging.debug("Cache hit. key = %s, count = %d, size = %d, total hit = %d, total miss = %d" % (key, len(cache.od), cache.size, wrapper.hits, wrapper.misses))
      else:
        value = user_function(*args, **kwargs)
        wrapper.misses += 1
        cache[key] = value
        logging.debug("Cache hit. key = %s, count = %d, size = %d, total hit = %d, total miss = %d" % (key, len(cache.od), cache.size, wrapper.hits, wrapper.misses))
      return value
    wrapper.hits   = 0
    wrapper.misses = 0
    return wrapper
  return decorating_function

if __name__ == '__main__':
  
  logging.basicConfig(level=logging.DEBUG)

  cache = LRUCache(max_size = 20*24)

  @lru_memoize(cache)
  def f(x, y=3):
    return x + y * 6

  for i in range(1000):
    f(random.randint(0,5), random.randint(0,5))
    print i, f.hits, f.misses, cache.size

  cache = LRUCache(max_count = 20)

  @lru_memoize(cache)
  def f(x, y=3):
    return x + y * 6

  for i in range(1000):
    f(random.randint(0,5), random.randint(0,5))
    print i, f.hits, f.misses, cache.size

