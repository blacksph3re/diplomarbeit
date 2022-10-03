import gym
from torch.utils.tensorboard.writer import SummaryWriter
from datetime import datetime

# Hparams
# log_act_prefix - how to prefix actions
# log_obs_prefix - how to prefix observations
# log_interval - every n steps to write out logs

class MaskedLogger(gym.Env):
  def __init__(self, env, hparams, logger):
    self.env = env
    
    self.action_space = env.action_space
    self.observation_space = env.observation_space
    self.metadata = env.metadata

    if logger != None:
      self.logger = logger
    else:
      self.logger = SummaryWriter('%s/%s' % (
        hparams.get_default('log_dir', 'logs'),
        hparams.get_default('run_name', str(datetime.now()))
      ))
  
    self.act_prefix = hparams.get_default('log_masked_act_prefix', 'act_masked')
    self.obs_prefix = hparams.get_default('log_masked_obs_prefix', 'obs_masked')
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
    }

  def get_act_labels(self):
    return {
      0: 'generator torque [Nm]',
      1: 'collective pitch [deg]',
    }