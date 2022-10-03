import gym
import numpy as np

# Polar-transforms the low speed shaft and/or high speed shaft positions
class PolarTransform(gym.Env):
  def __init__(self, env, hparams=None):
    self.env = env

    self.metadata = env.metadata

    self.transform_lowspeed = hparams.get_default('polar_transform_lss', True)
    self.transform_highspeed = hparams.get_default('polar_transform_hss', False)

    self.action_space = env.action_space
    obs_low = env.observation_space.low
    obs_high = env.observation_space.high

    if self.transform_highspeed:
      obs_low = np.append(obs_low, np.array([-np.inf, -np.inf]))
      obs_high = np.append(obs_high, np.array([np.inf, np.inf]))

    if self.transform_lowspeed:
      obs_low = np.append(obs_low, np.array([-np.inf, -np.inf]))
      obs_high = np.append(obs_high, np.array([np.inf, np.inf]))

    self.observation_space = gym.spaces.Box(
      low = obs_low,
      high = obs_high,
      dtype = env.observation_space.dtype,
    )
  
  def polar_transform(self, s):
    if self.transform_lowspeed:
      shaft_speed = s[29]
      assert shaft_speed >= 0 and shaft_speed <= 360
      shaft_speed = shaft_speed / 360 * 2 * np.pi
      s = np.append(s, np.array([
        np.sin(shaft_speed),
        np.cos(shaft_speed)
      ]))
    
    if self.transform_highspeed:
      shaft_speed = s[30]
      assert shaft_speed >= 0 and shaft_speed <= 360
      shaft_speed = shaft_speed / 360 * 2 * np.pi
      s = np.append(s, np.array([
        np.sin(shaft_speed),
        np.cos(shaft_speed)
      ]))
    
    return s

  def reset(self):
    s = self.env.reset()    
    return self.polar_transform(s)

  def step(self, action):
    s,r,d,i = self.env.step(action)
    return self.polar_transform(s), r, d, i

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()