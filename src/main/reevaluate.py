from garagewrapper import WindturbineGarageEnv, HParams
from helpers import get_broker_address
import garage
import sys
import os
import pickle
import datetime
import tqdm
import lzma
import gc
import toml
import tempfile
import shutil
import subprocess
from multiprocessing import Pool
from evaluate import eval_tasks


def sample_single_rollout(params):
  working_dir = tempfile.mkdtemp()

  # Load parameters
  nets = pickle.loads(params[0])
  policy = nets['policy']
  env = nets['env']
  config = params[1]

  # Load config from file
  with open(os.path.join(config['file']), 'r') as f:
    parsed = toml.load(f)

  parsed['server'] = parsed.get('server', {})
  parsed['server']['cycles'] = 1
  parsed['qblade']['pitch_actuator_model'] = True
  parsed['qblade']['project'] = "/opt/res/ML_SIM_NOFILTER"

  config['config_group'] = parsed['qblade']['group']
  client_env = env
  while not hasattr(client_env, 'is_client_env'):
    client_env = client_env.env
  
  client_env.env_config_group = config['config_group']
  
  conf_path = os.path.join(working_dir, 'tmp.toml')
  with open(conf_path, 'w') as f:
    toml.dump(parsed, f)

  subprocess.run('docker run -d --rm --net=host -e "OMP_NUM_THREADS=1" -e "OVERWRITE_CONFIG_FILE=/config/new.toml" -v "%s:/config/new.toml:ro" qblade_server' % str(conf_path), shell=True, capture_output=True)

  rollout = garage.rollout(env, policy, max_episode_length=env.spec.max_episode_length, deterministic=config['deterministic'])
  
  env.close()
  shutil.rmtree(working_dir)

  return ({'rollout': rollout, 'q': None, 'co': None}, config)


def main():
  assert len(sys.argv) >= 2, 'start the script with the location a file to be reevaluated'

  # eval_set = [
  #   {"deterministic": True, "file": "100_evallowwind.toml"},
  #   {"deterministic": True, "file": "101_evallowwind.toml"},
  #   {"deterministic": True, "file": "102_evallowwind.toml"},
  #   {"deterministic": True, "file": "103_evallowwind.toml"},
  #   {"deterministic": True, "file": "104_evallowwind.toml"},
  #   {"deterministic": True, "file": "105_evallowwind.toml"},
  #   {"deterministic": True, "file": "106_evallowwind.toml"},
  #   {"deterministic": False, "file": "107_evallowwind.toml"},
  # ]

  config_folder = "/home/sph3re/Programming/windturbine/src/main/experiments/steady_sweep"

  eval_set = [{'deterministic': True, 'file': x} for x in os.listdir(config_folder)]

  n_workers = 4


  broker_address = get_broker_address()
  print('Replacing broker address with %s' % broker_address)
  os.environ['OVERWRITE_ENV_BROKER_ADDRESS'] = broker_address

  print('Loading %s' % sys.argv[1])
  with lzma.open(sys.argv[1], 'r') as f:
    data = pickle.load(f)
  print(data['hparams'])

  policy = pickle.loads(data['policy'])
  env = pickle.loads(data['env'])
  pickled_nets = pickle.dumps({
    'policy': policy,
    'env': env,
  })

  # Bring tasks into the format for eval_tasks
  tasks = [(pickled_nets, {
    'deterministic': eval_run['deterministic'],
    'calc_q': False,
    # 'config_group': int(eval_run['file'].split('_')[0]),
    'file': os.path.join(config_folder, eval_run['file'])
  }) for eval_run in eval_set]

  print('Starting %d rollouts with %d workers at %s' % (len(tasks), n_workers, str(datetime.datetime.now())))
  newdata = {
    "hparams": data['hparams'],
    "time": datetime.datetime.now(),
    "policy": pickle.dumps(policy),
    "env": pickle.dumps(env)
  }

  newdata.update(eval_tasks(tasks, env.spec, n_workers, sample_single_rollout))


  if len(sys.argv) >= 3:
    filename = sys.argv[2]
  else:
    filename = '%s/steady_re%s' % (os.path.dirname(sys.argv[1]), os.path.basename(sys.argv[1]))
  with lzma.open(filename, 'wb') as f:
    pickle.dump(newdata, f)
  print('Written %s' % filename)

if __name__ == "__main__":
  main()