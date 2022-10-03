import gym
import numpy as np
import math

# Implements a discretized action space, either as a MultiDiscrete or Discrete distribution
# To be usable with differential control, it detects symmetric action spaces and in that case places one discrete action at 0 for each dimension
# and splits the rest of the action space
class DiscretizeActions(gym.Env):
  def __init__(self, env, hparams):
    self.env = env

    self.symmetric = hparams.get_default('discretization_symmetric', np.allclose(env.action_space.high, -env.action_space.low))
    
    # 9 discrete steps per dimension
    self.discretization = hparams.get_default('discretization_steps', 9)
    self.multi_discrete = hparams.get_default('discretization_use_multi', False)

    if not isinstance(self.discretization, list):
      self.discretization = [self.discretization for _ in range(len(env.action_space.low))]

    if self.multi_discrete:
      self.action_space = gym.spaces.MultiDiscrete(self.discretization)
    else:
      self.action_space = gym.spaces.Discrete(np.product(self.discretization))

    def bin_range(limit, count):
      return [(i+1)*(limit/count) for i in range(count)]

    self.bins = []
    for idx, num_bins in enumerate(self.discretization):
      if self.symmetric:
        cur_bins = [0] + bin_range(env.action_space.high[idx], math.ceil((num_bins-1)/2)) + bin_range(env.action_space.low[idx], math.floor((num_bins-1)/2))
      else:
        cur_bins = bin_range(env.action_space.high[idx] - env.action_space.low[idx], num_bins)
      self.bins.append(cur_bins)

    if not self.multi_discrete:
      # Enumerate all combinations of bins
      self.multi_conversion = np.array(np.meshgrid(*self.bins)).T.reshape(-1,len(self.bins))
    
    self.observation_space = env.observation_space
    self.metadata = env.metadata

  # Convert a discrete action to continous action space
  def convert_action(self, action):
    if not self.multi_discrete:
      if isinstance(action, int):
        pass
      elif isinstance(action, float):
        action = round(action)
      elif (isinstance(action, list) or isinstance(action, np.ndarray)) and len(action) == 1:
        action = action[0]
      else:
        raise TypeError('Action is of inappropriate type ' % type(action))

      return np.array(self.multi_conversion[action])
    else:
      assert len(action) == len(self.bins), 'Received an action of length %d while expecting %d' % (len(action), len(self.bins))

      return np.array([self.bins[i][action[i]] for i in range(len(action))])

  def reset(self):
    return self.env.reset()
  
  def step(self, action):
    action = self.convert_action(action)
    s,r,d,i = self.env.step(action)
    i["de_discretized_action"] = action
    return s,r,d,i

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()