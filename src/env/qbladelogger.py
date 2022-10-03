import gym
from torch.utils.tensorboard.writer import SummaryWriter
from datetime import datetime

# Hparams
# log_act_prefix - how to prefix actions
# log_obs_prefix - how to prefix observations
# log_interval - every n steps to write out logs

class QBladeLogger(gym.Env):
  def __init__(self, env, hparams, logger):
    self.env = env
    
    self.metadata = env.metadata
    self.action_space = env.action_space
    self.observation_space = env.observation_space

    if logger != None:
      self.logger = logger
    else:
      self.logger = SummaryWriter('%s/%s' % (
        hparams.get_default('log_dir', 'logs'),
        hparams.get_default('run_name', str(datetime.now()))
      ))
  
    self.act_prefix = 'act_raw'
    self.obs_prefix = 'obs_raw'
    self.log_interval = hparams.get_default('log_interval', 1)

    self.current_timestep = 0

  def step(self, action):
    self.log_action(action)
    s,r,d,i = self.env.step(action)
    self.log_observation(s)
    self.log_reward(r)
    self.current_timestep += 1

    return s,r,d,i
  
  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()
  
  def reset(self):
    return self.env.reset()

  def add_scalar(self, tag, val, step):
    if step % self.log_interval == 0:
      self.logger.add_scalar(tag, val, step)
    
  def log_reward(self, reward):
    self.add_scalar('%s/reward' % self.obs_prefix, reward, self.current_timestep)

  def log_action(self, action):
    for i in range(0, len(action)):
      self.add_scalar('%s/%s' % (self.act_prefix, self.get_act_labels()[i]), action[i], self.current_timestep)
  
  def log_observation(self, observation):
    for i in range(0, len(observation)):
      self.add_scalar('%s/%s' % (self.obs_prefix, self.get_obs_labels()[i]), observation[i], self.current_timestep)

  def get_obs_labels(self):
    return {
      0: 'rotational speed [rad/s]',
      1: 'power [kW]',
      2: 'HH wind velocity [m/s]',
      3: 'yaw angle [deg]',
      4: 'pitch blade 1 [deg]',
      5: 'pitch blade 2 [deg]',
      6: 'pitch blade 3 [deg]',
      7: 'tower top bending local x [Nm]',
      8: 'tower top bending local y [Nm]',
      9: 'tower top bending local z [Nm]',
      10: 'oop bending blade 1 [Nm]',
      11: 'oop bending blade 2 [Nm]',
      12: 'oop bending blade 3 [Nm]',
      13: 'ip bending blade 1 [Nm]',
      14: 'ip bending blade 2 [Nm]',
      15: 'ip bending blade 3 [Nm]',
      16: 'oop tip deflection blade 1 [m]',
      17: 'oop tip deflection blade 2 [m]',
      18: 'oop tip deflection blade 3 [m]',
      19: 'ip tip deflection blade 1 [m]',
      20: 'ip tip deflection blade 2 [m]',
      21: 'ip tip deflection blade 3 [m]',
      22: 'current time [s]'
    }

  def get_act_labels(self):
    return {
      0: 'generator torque [Nm]',
      1: 'yaw angle [deg]',
      2: 'pitch blade 1 [deg]',
      3: 'pitch blade 2 [deg]',
      4: 'pitch blade 3 [deg]'
    }