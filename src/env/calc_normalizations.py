from hparams import HParams
from envfactory import WindturbineEnv

import gym
import numpy as np
import time
import pandas as pd
import pickle

class OrnsteinUhlenbeckActionNoise():
  def __init__(self, mu, sigma, theta=.15, dt=1e-2, x0=None):
    self.theta = theta
    self.mu = mu
    self.sigma = sigma
    self.dt = dt
    self.x0 = x0
    self.reset()

  def __call__(self):
    x = self.x_prev + self.theta * (self.mu - self.x_prev) * self.dt + self.sigma * np.sqrt(self.dt) * np.random.normal(size=self.mu.shape)
    self.x_prev = x
    return x

  def reset(self):
    self.x_prev = self.x0 if self.x0 is not None else np.zeros_like(self.mu)

  def __repr__(self):
    return 'OrnsteinUhlenbeckActionNoise(mu={}, sigma={})'.format(self.mu, self.sigma)

state_memory = []

hparams = HParams(
  randomize_wind=False,
  clip_action_gradients=True,
  differential_control=False,
  coleman_transform=True,
  polar_transform=True,
  log_env=False,
  normalizing=False,
  mean_normalizing=False,
  mask=False,
  averaging=False,
  log_masked=False,
  freeze_actions=False,
  past_feeding=False,
  dilated_past_feeding=False,
  enable_ignore_steps=False,
  enable_trajectory_clip=False,
  delayed_rewards=False
)

multi_blade_outputs = [
  [4,5,6], # Pitch
  [7,8,9], # oop blade bending
  [10,11,12], # ip blade bending
  [13,14,15], # tor blade bending
  [16,17,18], # oop tip deflection
  [19,20,21], # ip tip deflection
]

def fix_norms(norm):
  for group in multi_blade_outputs:
    norm[group] = np.mean(norm[group])
  return norm


env = WindturbineEnv(hparams)

print('State space: %d, action space %d' % (env.observation_space.shape[0], env.action_space.shape[0]))
#env = gym.make('Pendulum-v0')

runs_per_trial = 2
steps_per_run = 2000

def rollout(env, policy):
  starttime = time.time()
  total_compute_time = 0
  s = env.reset()
  traj_state_memory = [s]
  deaths = 0

  for _ in range(0, steps_per_run):
    action = policy(s)
    s,r,d,i = env.step(action)
    traj_state_memory.append(s)
    total_compute_time += i['env_info']['compute_time']
    if d:
      env.reset()
      deaths += 1
  elapsed = time.time() - starttime
  print('Deaths: %d, Elapsed: %fs (%fs) - %f it/s' % (deaths, elapsed, total_compute_time, 1*steps_per_run/elapsed))

  return traj_state_memory

# Some steps running with zero 
for _ in range(0, runs_per_trial):
  print('Zero actions')
  state_memory.append(rollout(env, lambda x: np.zeros(env.action_space.shape)))

# Some steps running with maximum 
for _ in range(0, runs_per_trial):
  print('Max actions')
  state_memory.append(rollout(env, lambda x: env.action_space.high))


# Some steps running with minimum 
for _ in range(0, runs_per_trial):
  print('Min actions')
  state_memory.append(rollout(env, lambda x: env.action_space.low))


# Some steps with low random noise around zero
for _ in range(0, runs_per_trial):
  print('Low white noise')
  state_memory.append(rollout(env, lambda x: np.random.normal(env.action_space.shape) * (env.action_space.high - env.action_space.low) * 0.01))

# Some steps with high random noise around zero
for _ in range(0, runs_per_trial):
  print('High white noise')
  state_memory.append(rollout(env, lambda x: np.random.normal(env.action_space.shape) * (env.action_space.high - env.action_space.low) * 0.1))

#img = Image.fromarray(env.render())

# Some steps with low OU noise
for _ in range(0, runs_per_trial):
  print('Low OU noise')
  noise = OrnsteinUhlenbeckActionNoise(mu=np.zeros(env.action_space.shape), sigma=(env.action_space.high - env.action_space.low) * 0.1, dt=0.1)
  state_memory.append(rollout(env, lambda x: noise()))
  

# Some steps with high OU noise
for _ in range(0, runs_per_trial):
  print('High OU noise')
  noise = OrnsteinUhlenbeckActionNoise(mu=np.zeros(env.action_space.shape), sigma=(env.action_space.high - env.action_space.low) * 0.5, dt=0.1)
  state_memory.append(rollout(env, lambda x: noise()))


data = np.array(state_memory)
data = np.reshape(data, (-1, data.shape[-1]))

print('Max: ', fix_norms(np.max(data, axis=0)))
print('99% quantile: ', fix_norms(np.quantile(data, 0.99, axis=0)))
print('95% quantile: ', fix_norms(np.quantile(data, 0.95, axis=0)))
print('5% quantile: ', fix_norms(np.quantile(data, 0.05, axis=0)))
print('1% quantile: ', fix_norms(np.quantile(data, 0.01, axis=0)))
print('Min: ', fix_norms(np.min(data, axis=0)))
print('Mean: ', fix_norms(np.mean(data, axis=0)))
print('Std: ', fix_norms(np.std(data, axis=0)))

with open('normalisation_data.pkl', 'wb') as f:
  pickle.dump({
    "states": state_memory,
    "mean": fix_norms(np.mean(data, axis=0)),
    "std": fix_norms(np.std(data, axis=0)),
    "hparams": hparams,
  }, f)
