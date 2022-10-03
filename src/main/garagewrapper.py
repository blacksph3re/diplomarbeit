# This file wraps the env into a garage-compatible environment
import sys
import os

try:
  sys.path.insert(1, os.path.abspath('%s/../env' % os.path.dirname(os.path.abspath(__file__))))
except:
  sys.path.insert(1, os.path.abspath('%s/../env' % os.path.dirname(os.path.abspath(sys.argv[0]))))

from envfactory import makeenv
from hparams import HParams
from test_connection import test_connection

import akro
import gym
import numpy as np
import garage
import pickle
import time
import datetime

class WindturbineGarageEnv(garage.Environment):
  def __init__(self, hparams):
    self.hparams = hparams
    self.env = makeenv(hparams)

    # Loop down to the client env to invoke some functions directly
    self.client = self.env
    while hasattr(self.client, 'env'):
      self.client = self.client.env

    self.steps_since_reset = None
    self.spec

  def reset(self):
    self.steps_since_reset = 0
    start_time = time.time()
    s = self.env.reset()
    self.reset_time = start_time - time.time()
    return s, {}

  def step(self, action):
    start_time = time.time()
    s,r,d,i = self.env.step(action)

    # hack to reset the env when the episode is over
    # but store the backup in case we still need to work
    self.steps_since_reset += 1
    if self.steps_since_reset == self.spec.max_episode_length:
      self.client.load_before_next_step = self.client.request_serialized()
      self.client.request_reset()
    
    self.step_time = start_time - time.time()

    return garage.EnvStep(
      self.spec,
      action,
      r,
      s,
      i,
      garage.StepType.MID if not d else garage.StepType.TERMINAL
    )

  def render(self, mode=None):
    return self.env.render()

  def visualize(self):
    pass
    
  def close(self):
    return self.env.close()

  @property
  def action_space(self):
    return akro.from_gym(self.env.action_space)

  @property
  def observation_space(self):
    return akro.from_gym(self.env.observation_space)

  @property
  def spec(self):
    return garage.EnvSpec(self.observation_space, self.action_space, self.hparams.get_default('max_trajectory_length', 2000))

  @property
  def render_modes(self):
    return ['rgb_array']
