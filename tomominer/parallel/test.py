
from tomominer.parallel import Runner, Task

r = Runner(('127.0.0.1', 5011))

t = Task(r.proj_id, 'queue_stats_string',)
r.run_single(t, None)

