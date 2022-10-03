from multiprocessing import Pool
import subprocess
import os
import itertools
import tqdm
import time
import json
import toml
from helpers import get_broker_address, start_training, resume_training

with open(os.getenv("GRIDSEARCH_HPARAM_FILE"), 'r') as f:
  hparams = json.load(f)

broker_address=get_broker_address()
os.environ['OVERWRITE_ENV_BROKER_ADDRESS'] = broker_address
hparams["env_broker_address"] = broker_address

if os.getenv("N_SAMPLE_WORKERS"):
  hparams['n_sample_workers'] = int(os.getenv("N_SAMPLE_WORKERS"))

if os.getenv('RESULT_DIR'):
  hparams['snapshot_dir'] = os.getenv('RESULT_DIR')
os.makedirs(hparams['snapshot_dir'], exist_ok=True)

hparams['code_dir'] = os.getenv('PYTHON') + '/main' if os.getenv('PYTHON') else os.getcwd(),

if os.getenv('LOG_DIR'):
  hparams['log_dir'] = os.getenv('LOG_DIR')

if hparams['log_dir'] is None:
  hparams['log_dir'] = hparams['snapshot_dir']
os.makedirs(hparams['log_dir'], exist_ok=True)

if os.getenv('ENV_CONFIG_FILES'):
  def load_toml_config(file):
    try:
      with open(file, 'r') as f:
        return toml.load(f)
    except:
      return {}
      
  hparams['env_config_files'] = [load_toml_config(file) for file in os.getenv('ENV_CONFIG_FILES').split(':')]

print('Starting gridsearch with global hparams:')
print(hparams)

agent_rank = int(os.getenv('AGENT_RANK')) if os.getenv('AGENT_RANK') else 0
agent_count = int(os.getenv('AGENT_COUNT')) if os.getenv('AGENT_COUNT') else 1
n_tune_workers = int(os.getenv('N_TUNE_WORKERS')) if os.getenv('N_TUNE_WORKERS') else 2
assert agent_rank < agent_count

if agent_rank == 0:
  with open('%s/global_hparams.json' % hparams['snapshot_dir'], 'w') as f:
    json.dump(hparams, f)

# Find keys which are to be searched
search_space = dict([(key, value['grid_search']) for (key, value) in hparams.items() if isinstance(value, dict) and 'grid_search' in value])

# Add explicit grid searches
if 'grid_search' in hparams.keys():
  search_space['grid_search'] = hparams['grid_search']

# Calculate the product set
search_space = [dict(zip(search_space.keys(), a)) for a in itertools.product(*search_space.values())]

# Move explicit grid_searches up
search_space = [(dict({key:value for (key,value) in d.items() if key != 'grid_search'}, **d['grid_search']) if 'grid_search' in d else d) for d in search_space]


if agent_rank == 0:
  print('%d hyperparameter combinations tackled by %d agent nodes with %d workers: ' % (len(search_space), agent_count, n_tune_workers))
  print('\n'.join([str(x) for x in search_space]))

# Combine that with original hparams
search_space = [hparams | x for x in search_space]
# Merge special key to outer hparams
#TODO
# Limit to the runs for our current rank
search_space = [(i, x) for i, x in enumerate(search_space) if (agent_count + i - agent_rank) % agent_count == 0]

assert len(search_space) <= n_tune_workers, 'You specified more jobs than workers, feeling overwhelmed and panicking'

def run_single_evaluation(task):
  taskid, hparams = task

  hparams['snapshot_dir'] = '%s/data_%d' % (hparams['snapshot_dir'], taskid)
  hparams['tune_trial_id'] = taskid

  print('Starting task %s' % str(taskid))
  
  progress, cur_progress = start_training(hparams, {'env_broker_address': broker_address, 
                                                    'n_sample_workers': hparams['n_sample_workers'],
                                                    'n_epochs': hparams['n_epochs']})

  last_iter = progress['Evaluation/Iteration'].max()
  print('Entering resume loop at %d' % last_iter)

  while last_iter < hparams['n_epochs']:
    progress, cur_progress = resume_training(hparams, progress)
    last_iter = progress['Evaluation/Iteration'].max()


pool = Pool(processes=n_tune_workers)
start_time = time.time()
for _ in pool.map(run_single_evaluation, search_space):
  pass
end_time = time.time()

pool.close()

print('Ran training in %f seconds' % (end_time - start_time))
