import gym
import numpy as np

# This is very similar to averaging, only that it does not average across states but only across rewards
# Instead it discards ignore_steps steps completely
class IgnoreSteps(gym.Env):
  def __init__(self, env, hparams):
    self.env = env
    self.action_space = env.action_space
    self.observation_space = env.observation_space

    self.ignore_steps = hparams.get_default('ignore_steps', 2)

  def reset(self):
    return self.env.reset()
  
  def step(self, action):
    past_r = []

    for i in range(0, self.ignore_steps+1):
      s,r,d,i = self.env.step(action)
      past_r.append(r)

      if d:
        break
    
    return s, np.mean(past_r), d, i
  
  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()