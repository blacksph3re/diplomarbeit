from garage.experiment import Snapshotter
from garagewrapper import WindturbineGarageEnv, HParams
from helpers import get_broker_address
import garage
import sys
import os
import pickle
import datetime
import tqdm
import torch
import lzma
import gc
import numpy as np
from multiprocessing import Pool



def sample_single_rollout(params):
  nets = pickle.loads(params[0])
  policy = nets['policy']
  env = nets['env']
  config = params[1]

  # Overwrite the config group if desired
  config_group = config['config_group']
  client_env = env
  while not hasattr(client_env, 'is_client_env'):
    client_env = client_env.env
  
  if config_group:
    client_env.env_config_group = config_group
  else:
    config_group = client_env.env_config_group

  rollout = garage.rollout(env, policy, max_episode_length=env.spec.max_episode_length, deterministic=config['deterministic'])
  env.close()

  if config.get('calc_q', False):
    obs = torch.tensor(rollout['observations'], dtype=torch.float32)
    act = torch.tensor(rollout['actions'], dtype=torch.float32)
    qf1 = nets['qf1']
    qf2 = nets['qf2']
    with torch.no_grad():
      q1 = qf1(obs, act)
      q2 = qf2(obs, act)
      q = torch.cat([q1, q2], axis=1).numpy()

      # Feature co-adaptation after DR3
      def coadaptation(qf, obs, act):
        phi = torch.cat([obs,act], 1)
        for layer in qf1._layers:
          phi = layer(phi)
        coadaptation = np.mean([torch.dot(phi[i], phi[i+1]) for i in range(len(phi)-1)])
        return coadaptation

      co = np.stack([coadaptation(qf1, obs, act), coadaptation(qf2, obs, act)])

  else:
    q = None
    co = None

  return ({'rollout': rollout, 'q': q, 'co': co}, config)

def eval_tasks(tasks, env_spec, n_workers, sample_single_rollout):
  pool = Pool(processes=n_workers)
  tmp = list(tqdm.tqdm(pool.imap_unordered(sample_single_rollout, tasks), total=len(tasks)))
  pool.close()

  # Sort by group
  tmp.sort(key=lambda item: item[1]['config_group'])

  det_runs = [(r, config) for (r, config) in tmp if config['deterministic']]
  nondet_runs = [(r, config) for (r, config) in tmp if config['deterministic'] is False]

  res = [r['rollout'] for (r, _) in det_runs]
  if len(res):
    episodes_deterministic = garage.EpisodeBatch.from_list(env_spec, res)
  else:
    print('no deterministic rollouts')
    episodes_deterministic = None

  res = [r['rollout'] for (r, _) in nondet_runs]
  if len(res):
    episodes_nondeterministic = garage.EpisodeBatch.from_list(env_spec, res)
  else:
    print('no non-deterministic rollouts')
    episodes_nondeterministic = None

  return {
    "episodes": episodes_deterministic,
    "config_groups": [config['config_group'] for (_, config) in det_runs],
    "q": [r['q'] for (r, _) in det_runs],
    "co": [r['co'] for (r, _) in det_runs],
    "episodes_nondeterministic": episodes_nondeterministic,
    "config_groups_nondeterministic": [config['config_group'] for (_, config) in nondet_runs],
    "q_nondeterministic": [r['q'] for (r, _) in nondet_runs],
    "co_nondeterministic": [r['co'] for (r, _) in nondet_runs],
  }

def main():
  assert len(sys.argv) >= 2, 'start the script with the location of training run'
  hparams = HParams()
  print('Reading from %s' % sys.argv[1])
  with open('%s/hparams.json' % sys.argv[1], 'r') as f:
    hparams.parse_json(f.read())
  print(hparams)

  assert 'eval_set' in hparams, 'no eval set specified'

  assert len(sys.argv) >= 3, 'start the script with the iteration to evaluate'
  iteration = int(sys.argv[2])
  assert os.path.exists('%s/itr_%d.pkl' % (sys.argv[1], iteration)), 'iteration to evaluate does not exist!'

  if os.path.exists('%s/eval_%d.xz' % (sys.argv[1], iteration)):
    print('Warning - this iteration has been evaluated already!')

  # Mark us working (race cond from check before to this :D)
  # with lzma.open('%s/eval_%d.xz' % (sys.argv[1], iteration), 'wb') as f:
  #   pickle.dump({"status": "I am working on it!"}, f)

  n_workers = int(os.getenv('N_SAMPLE_WORKERS') or 1)

  try:
    broker_address = get_broker_address()
    print('Replacing broker address with %s' % broker_address)
    os.environ['OVERWRITE_ENV_BROKER_ADDRESS'] = broker_address

    snapshotter = Snapshotter()
    print('Loading %s, itr %d' % (sys.argv[1], iteration))
    data = snapshotter.load(sys.argv[1], iteration)

    print('Loaded snapshot, preparing')

    policy = data['algo'].policy
    env = data['env']
    if isinstance(env, list):
      env = env[0]

    qf1 = data['algo']._qf1 if '_qf1' in dir(data['algo']) else None
    qf2 = data['algo']._qf2 if '_qf2' in dir(data['algo']) else None
    
    # Try to delete + shutdown the rest of the unpickled things
    data['algo']._sampler.shutdown_worker()
    del data
    gc.collect()

    pickled_nets = pickle.dumps({
      'policy': policy,
      'env': env,
      'qf1': qf1,
      'qf2': qf2
    })

    def default_config(conf):
      conf['deterministic'] = conf.get('deterministic', True)
      conf['config_group'] = conf.get('config_group', hparams['env_config_group'])
      conf['calc_q'] = conf.get('calc_q', True)
      return conf

    tasks = [(pickled_nets, default_config(conf)) for conf in hparams['eval_set']]

    print('Starting %d rollouts with %d workers at %s' % (len(tasks), n_workers, str(datetime.datetime.now())))
    data = eval_tasks(tasks, env.spec, n_workers, sample_single_rollout)

    # Add some additional information
    data.update({
      "hparams": hparams.get_dict(),
      "time": datetime.datetime.now(),
      "policy": pickle.dumps(policy), # Double pickle so it doesn't load if not necessary
      "env": pickle.dumps(env),
      "qf1": pickle.dumps(qf1),
      "qf2": pickle.dumps(qf2)
    })
    
    with lzma.open('%s/eval_%d.xz' % (sys.argv[1], iteration), 'wb') as f:
      pickle.dump(data, f)
    
  except Exception as e:
    print(e)
    os.remove('%s/eval_%d.xz' % (sys.argv[1], iteration))
    raise e

  exit(0)

if __name__ == '__main__':
  main()