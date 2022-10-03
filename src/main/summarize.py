# Start on hlrn with srun --pty -n1 -N1 -c96 --hint=compute_bound python summarize.py

import os
import pickle 
import lzma
import json
import tqdm
import garage
from multiprocessing import Pool
import numpy as np
import pandas as pd
from helpers import recover_progress
import rainflow
from collections import namedtuple



def calc_del(signal, dt=0.1, fdel=1, m=1, skip=300):
  signal = signal[skip:]
  rainflow_data = np.array(rainflow.count_cycles(signal, nbins=128))
  
  # rainflow_data = np.array(list(rainflow.extract_cycles(signal)))
  # lm = rainflow_data[:,1]

  lr = rainflow_data[:,0]
  n = rainflow_data[:,1]

  # lrf = lr * ((lult - np.abs(lmf)) / (lult - np.abs(lm)))
  lrf = lr

  T = len(signal)*dt
  nsteq = fdel*T

  delst = (np.sum(np.sum(n * lrf ** m)) / np.sum(nsteq)) ** (1/m)
  return delst

def calc_extreme(signal, skip=300, q=0.99):
  return np.quantile(signal[skip:], q)



def evaluate_episodes(episodes, coadaptation=None):
  num_episodes = len(episodes.lengths)
  Episode = namedtuple('Episode', 'start end')
  borders = [Episode(sum(episodes.lengths[:i]), sum(episodes.lengths[:i+1])) for i in range(num_episodes)]
  rewards = [sum(episodes.rewards[b.start:b.end]) for b in borders]
  # Hack for sac-fullturb-3
  if 'reward_composition' not in episodes.env_infos:
    episodes.env_infos['reward_composition'] = {
        'coleman_reward': episodes.env_infos['coleman_reward'],
        'coleman_action_reward': episodes.env_infos['coleman_action_reward'],
    }
  def parse_composition(comp, b):
    if comp is None:
      return {}
    return dict([('rc_'+key, sum(value[b.start:b.end])) for (key, value) in comp.items()])
  reward_composition = [parse_composition(episodes.env_infos.get('reward_composition', None), b) for b in borders]
  windspeeds = [np.mean(episodes.env_infos['env_info']['wind_info']['windspeed'][b.start:b.end]) for b in borders]
  inflow = [np.mean(episodes.env_infos['env_info']['wind_info']['inflow_angle_hor'][b.start:b.end]) for b in borders]
  group = [episodes.env_infos['env_info']['group'][b.start] for b in borders]
  states = [episodes.env_infos['orig_state'][b.start:b.end] for b in borders]
  sampling_freq = 10 # 10 simulation steps per sec
  pitch_travel = [np.mean(np.abs(np.diff(s[:,[4,5,6]], axis=0))) for s in states]
  # blade DELs
  death = [episodes.lengths[i] < max(episodes.lengths) for i in range(num_episodes)]
  DEL1 = [calc_del(s[:,7], dt=1/sampling_freq, fdel=1, m=10, skip=300) for s in states]
  DEL2 = [calc_del(s[:,8], dt=1/sampling_freq, fdel=1, m=10, skip=300) for s in states]
  DEL3 = [calc_del(s[:,9], dt=1/sampling_freq, fdel=1, m=10, skip=300) for s in states]
  # pitch DELs
  pDEL1 = [calc_del(s[:,4], dt=1/sampling_freq, fdel=1, m=1, skip=300) for s in states]
  pDEL2 = [calc_del(s[:,5], dt=1/sampling_freq, fdel=1, m=1, skip=300) for s in states]
  pDEL3 = [calc_del(s[:,6], dt=1/sampling_freq, fdel=1, m=1, skip=300) for s in states]
  # extreme
  extreme1 = [calc_extreme(s[:,7], skip=300, q=0.99) for s in states]
  extreme2 = [calc_extreme(s[:,8], skip=300, q=0.99) for s in states]
  extreme3 = [calc_extreme(s[:,9], skip=300, q=0.99) for s in states]
  
  power = [np.mean(s[300:, 1]) for s in states]

  if coadaptation is None:
    coadaptation = [None for _ in range(num_episodes)]
  else:
    coadaptation = [(np.mean(co) if co is not None else None) for co in coadaptation]

  return [{
    **reward_composition[i],
    "reward": rewards[i],
    "windspeed": windspeeds[i],
    "inflow_angle_hor": inflow[i],
    "group": group[i],
    "lengths": episodes.lengths[i],
    "death": death[i],
    "pitch_travel": pitch_travel[i],
    "DEL1": DEL1[i],
    "DEL2": DEL2[i],
    "DEL3": DEL3[i],
    "pDEL1": pDEL1[i],
    "pDEL2": pDEL2[i],
    "pDEL3": pDEL3[i],
    "extreme1": extreme1[i],
    "extreme2": extreme2[i],
    "extreme3": extreme3[i],
    "power": power[i],
    "coadaptation": coadaptation[i]} for i in range(len(windspeeds))]

def read_single_run(x):
  folder, iteration = x

  try:
    with lzma.open('%s/eval_%s.xz' % (folder, iteration), 'rb') as f:
      data = pickle.load(f)
    
    if data['episodes'] is not None:
      rewards = evaluate_episodes(data['episodes'], data.get('co', None))
    else:
      rewards = []
    
    if data['episodes_nondeterministic'] is not None:
      nondet_rewards = evaluate_episodes(data['episodes_nondeterministic'], data.get('co_nondeterministic', None))
    else:
      nondet_rewards = []
    assert len(rewards) or len(nondet_rewards), 'neither deterministic nor non-deterministic episodes found'

    del data
    return folder, iteration, rewards, nondet_rewards
  except Exception as e:
    print('Could not read %s/eval_%s.xz:' % (folder, iteration), e)
    return folder, iteration, np.array([]), np.array([])

def main():
  result_dir = os.getenv('RESULT_DIR')
  assert os.path.exists(result_dir)

  n_processes = 40

  if os.getenv('SLURM_CPUS_PER_TASK'):
    n_processes = int(os.getenv('SLURM_CPUS_PER_TASK'))

  dirs = ["%s/%s" % (result_dir, x) for x in os.listdir(result_dir) if x.startswith('data')]
  tasks = [(d, x[5:-3]) for d in dirs for x in os.listdir(d)if x.startswith('eval_')]
  tasks.sort()
  assert len(tasks)

  pool = Pool(processes=n_processes)
  print('Reading eval files with %d processes' % n_processes)
  results = list(tqdm.tqdm(pool.imap_unordered(read_single_run, tasks), total=len(tasks)))
  pool.close()
  def load_hparams(file):
    with open(file, 'r') as f:
      data = json.load(f)
    return data

  global_hparams = load_hparams('%s/global_hparams.json' % result_dir)
  grid_searches = [key for (key, value) in global_hparams.items() if isinstance(value, dict) and 'grid_search' in value]
  if 'grid_search' in global_hparams.keys():
    grid_searches = grid_searches + list(set([key for d in global_hparams['grid_search'] for key in d.keys()]))
  hparams = dict([(d, load_hparams('%s/hparams.json' % d)) for d in dirs])

  def transform_row(d, i, det, v):
    cols = dict([(key, hparams[d].get(key, None)) for key in grid_searches])
    cols['iteration'] = i
    cols['folder'] = os.path.basename(d)
    cols['deterministic'] = det
    for key in v.keys():
      cols[key] = v[key]

    return cols

  data = pd.DataFrame([transform_row(d, i, True, v) for (d, i, res, _) in results for v in res] + [transform_row(d, i, False, v) for (d, i, _, res) in results for v in res])

  def read_progress(d):
    try:
      return recover_progress(d)
    except Exception as e:
      print('Could not parse progress from %s' % d)
      print(e)
      return pd.DataFrame()

  try:
    total_progresses = pd.concat([read_progress('%s' % (d)).assign(folder=os.path.basename(d)) for d in dirs]).rename(columns={'Evaluation/Iteration': 'iteration'})
    data['iteration'] = data['iteration'].apply(int)
    data = pd.merge(data, total_progresses, how='left', on=['folder', 'iteration'])
  except Exception as e:
    print(e)


  print('Writing summary to %s/summary.csv' % result_dir)
  data.to_csv('%s/summary.csv' % result_dir, index=False)

if __name__ == '__main__':
  main()