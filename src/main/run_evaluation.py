from multiprocessing import Pool
import subprocess
import os
import tqdm
import time
import random
import lzma
import pickle
from helpers import get_broker_address

code_dir = os.getenv('PYTHON') + '/main' if os.getenv('PYTHON') else os.getcwd()
result_dir = os.getenv('RESULT_DIR')
n_workers = int(os.getenv('N_TUNE_WORKERS'))
agent_rank = int(os.getenv('AGENT_RANK')) if os.getenv('AGENT_RANK') else 0
agent_count = int(os.getenv('AGENT_COUNT')) if os.getenv('AGENT_COUNT') else 1

print('Running post-processing with res dir %s, code dir %s and %d workers on %d nodes' % (result_dir, code_dir, n_workers, agent_count))

broker_address = get_broker_address()
os.environ['OVERWRITE_ENV_BROKER_ADDRESS'] = broker_address

dirs = ["%s/%s" % (result_dir, x) for x in os.listdir(result_dir) if x.startswith('data')]
tasks = [(d, int(x[4:-4])) for d in dirs for x in os.listdir(d) if x.startswith('itr_')]
tasks.sort()
# Limit to current rank
own_tasks = [x for i, x in enumerate(tasks) if (agent_count + i - agent_rank) % agent_count == 0]


print('Found %d checkpoints in %d trials, tackling %d on this node' % (len(tasks), len(dirs), len(own_tasks)))

def assert_eval_success(folder, iteration):
  iteration = str(iteration)
  #assert os.path.exists('%s/eval-%s.xz' % (folder, iteration)), "Eval file does not exist!"

  with lzma.open('%s/eval_%s.xz' % (folder, iteration), 'rb') as f:
    data = pickle.load(f)
  assert "episodes" in data
  assert sum(data["episodes"].lengths) > 0

def run_single_evaluation(task):
  folder, iteration = task
  already_evaluated = True
  try:
    assert_eval_success(folder, iteration)
  except:
    already_evaluated = False
  if already_evaluated:
    return

  # Retry 5 times
  for i in range(5):
    try:
      with open('%s/worker-%d-%d.log' % (os.getenv('LOG_DIR'), agent_rank, os.getpid()), 'a') as f:
        subprocess.call(['python', '%s/evaluate.py' % code_dir, folder, str(iteration)], stdout=f, stderr=subprocess.STDOUT, env=os.environ, timeout=900)
      assert_eval_success(folder, iteration)
    except Exception as e:
      print('An error occured during evaluation on worker %d try %d: %s' % (os.getpid(), i, str(e)))
      time.sleep(random.uniform(2, 20))
      continue

    break


pool = Pool(processes=n_workers)
start_time = time.time()
for _ in tqdm.tqdm(pool.imap_unordered(run_single_evaluation, own_tasks), total=len(own_tasks)):
  pass
end_time = time.time()

print('Evaluation done, it took %f secs' % (end_time - start_time))

pool.close()

if agent_count == 0:
  print('Starting a summary run')
  subprocess.call(['python', '%s/summarize.py' % code_dir])