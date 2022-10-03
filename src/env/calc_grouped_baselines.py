# Calculates a baseline performance of just the controller (zero differential control)

from hparams import HParams
from envfactory import WindturbineEnv

import gym
import numpy as np
import time
import pandas as pd
import pickle
from multiprocessing import Pool
import tqdm
import toml
import tempfile
import os
import shutil
import subprocess
import lzma

steps_per_run = 2000
n_workers = 4
nruns = 1
config_folder = "/home/sph3re/Programming/windturbine/src/main/experiments/actuator_fullturb"
configs = os.listdir(config_folder)
hparams = HParams(
  randomize_wind=False,
  clip_action_gradients=True,
  log_env=False,
  normalizing=False,
  mean_normalizing=False,
  mask=True,
  mask_obs=None,
  mask_act='coleman-no-torque',
  averaging=False,
  log_masked=False,
  freeze_actions=False,
  past_feeding=False,
  dilated_past_feeding=False,
  enable_ignore_steps=False,
  enable_trajectory_clip=False,
  delayed_rewards=False,
  differential_control= False,
  coleman_transform= True,
  reward_hold_speed_factor= 0,
  reward_max_power_factor= 0,
  reward_max_speed_factor= 0,
  reward_min_speed_factor= 0,
  reward_excess_power_factor= 0,
  reward_pitch_fluctuation= 0,
  reward_torque_fluctuation= 0,
  reward_blade_bending= 0,
  reward_tower_bending_factor_x= 0,
  reward_tower_bending_factor_y= 0,
  reward_coleman_factor= 1,
  reward_constant_offset= 1,
)

# print(hparams)
# print('State space: %d, action space %d' % (global_env.observation_space.shape[0], global_env.action_space.shape[0]))
def evaluate_config(params):
  conf, hparams = params
  #print('Evaluating %s' % conf)
  working_dir = tempfile.mkdtemp()

  with open(os.path.join(config_folder, conf), 'r') as f:
    parsed = toml.load(f)

  parsed['server'] = parsed.get('server', {})
  parsed['server']['cycles'] = nruns
  parsed['qblade']['pitch_actuator_model'] = False
  parsed['qblade']['project'] = "/opt/res/ML_SIM_IPC"
  # parsed['qblade']['project'] = "/opt/res/ML_SIM"

  conf_path = os.path.join(working_dir, 'tmp.toml')
  with open(conf_path, 'w') as f:
    toml.dump(parsed, f)

  subprocess.run('docker run -d --rm --net=host -e "OMP_NUM_THREADS=1" -e "OVERWRITE_CONFIG_FILE=/config/new.toml" -v "%s:/config/new.toml:ro" qblade_server' % str(conf_path), shell=True, capture_output=True)

  hparams['env_config_group'] = parsed['qblade']['group']

  # Some steps running with zero 
  rewards = []
  compositions = []
  states = []
  infos = []
  deaths = 0

  def rollout(hparams):
    env = WindturbineEnv(hparams)
    traj_deaths = 0
    traj_rewards = []
    traj_compositions = []
    traj_states = []
    traj_infos = []
    env.reset()

    for _ in range(0, steps_per_run):
      action = np.zeros(env.action_space.shape)
      s,r,d,i = env.step(action)
      traj_rewards.append(r)
      traj_compositions.append(i['reward_composition'])
      traj_states.append(s)
      traj_infos.append(i)
      if d:
        traj_deaths += 1
    
    return traj_rewards, traj_compositions, traj_states, traj_deaths, traj_infos


  for _ in range(nruns):
    traj_rewards, traj_compositions, traj_states, traj_deaths, traj_infos = rollout(hparams)
    
    rewards.append(traj_rewards)
    compositions.append(traj_compositions)
    states.append(traj_states)
    infos.append(traj_infos)
    deaths += traj_deaths


  rewards = pd.DataFrame(rewards)

  # print('Episode mean')
  # print(rewards.mean(axis=1))
  # print('Episode std')
  # print(rewards.std(axis=1))

  # print('Episode 1% Quantile')
  # print(rewards.quantile(0.01, axis=1))
  # print('Episode 5% Quantile')
  # print(rewards.quantile(0.05, axis=1))
  # print('Episode 95% Quantile')
  # print(rewards.quantile(0.95, axis=1))
  # print('Episode 99% Quantile')
  # print(rewards.quantile(0.99, axis=1))

  # print('Mean')
  # print(rewards.mean().mean())
  # print('Std')
  # print(rewards.std().std())

  with lzma.open('../../results/baselines/actuator_fullturb_ipc/reward_data_%s.xz' % (conf.split('.')[0]), 'wb') as f:
    pickle.dump({
      "rewards": rewards,
      "compositions": compositions,
      "states": states,
      "hparams": hparams.get_dict()
    }, f)

  shutil.rmtree(working_dir)
  return True


pool = Pool(processes=n_workers)
print('Baseline calculations for %d configs by %d workers' % (len(configs), n_workers))
for _ in tqdm.tqdm(pool.imap_unordered(evaluate_config, [(c, hparams) for c in configs]), total=len(configs)):
  pass
pool.close()