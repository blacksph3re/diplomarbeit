import gym
import numpy as np

class Averager(gym.Env):
  def __init__(self, env, hparams):
    self.env = env
    self.action_space = env.action_space
    self.observation_space = env.observation_space

    self.averaging_steps = hparams.get_default('averaging_steps', 4)

  def reset(self):
    return self.env.reset()
  
  def step(self, action):
    past_s = []
    past_r = []
    past_d = []

    for i in range(0, self.averaging_steps):
      s,r,d,i = self.env.step(action)
      past_s.append(s)
      past_r.append(r)
      past_d.append(d)

      if d:
        break
    
    return np.mean(past_s, axis=0), np.mean(past_r, axis=0), np.any(past_d), i
  
  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()