import gym
import numpy as np
from pyts.image import GramianAngularField


# Encode the past as a gramian angular field

class GramianAngularField(gym.Env):
  def __init__(self, env, hparams):
    self.env = env

    self.metadata = env.metadata

    self.action_space = env.action_space
    
    self.gaf_resolution = hparams.get_default('gaf_resolution', 32)
    self.transformer = GramianAngularField(image_size=self.gaf_resolution, method='summation')

    self.observation_space = gym.spaces.Box(
      low = -1.0,
      high = 1.0,
      shape = (len(env.observation_space.low), self.gaf_resolution, self.gaf_resolution), # Channel, Height, Width
      dtype = env.observation_space.dtype,
    )

    self.buffer = []
  
  def gaf_encode(self):
    past = np.array(self.buffer)

    if past.shape[0] < self.gaf_resolution:
      past = np.concatenate([
        np.zeros(shape=(self.gaf_resolution - len(self.buffer), len(self.env.observation_space.low))),
        past
      ], axis=0)
    
    return self.transformer.transform(past.transpose(1,0))

  def reset(self):
    obs = self.env.reset()
    self.buffer = [obs]
    return self.gaf_encode()
  
  def step(self, action):
    s,r,d,i = self.env.step(action)

    self.buffer.append(s)
    while len(self.buffer) > self.gaf_resolution:
      self.buffer.pop(0)

    return self.gaf_encode(),r,d,i
  
  def close(self):
    return self.env.close()

  def render(self):
    return self.env.render()
  

  