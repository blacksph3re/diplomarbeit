import gym
import numpy as np

class Pastfeeder(gym.Env):
  def __init__(self, env, hparams):
    self.env = env

    self.metadata = env.metadata

    self.action_space = env.action_space
    
    self.past_feeding_steps = hparams.get_default('past_feeding_steps', 3)
    self.observation_space = gym.spaces.Box(
      low = np.concatenate(tuple([env.observation_space.low for _ in range(0, self.past_feeding_steps)])),
      high = np.concatenate(tuple([env.observation_space.high for _ in range(0, self.past_feeding_steps)])),
      dtype = env.observation_space.dtype,
    )

    self.single_obs_length = env.observation_space.shape[0]

    self.past_steps = np.array([])
  
  def override_past(self, obs):
    self.past_steps = np.concatenate(tuple([obs for _ in range(0, self.past_feeding_steps)]))
  
  def shift_in(self, obs):
    # Check for the correct length
    if len(self.past_steps) == self.single_obs_length * self.past_feeding_steps:
      self.past_steps = np.concatenate((obs, self.past_steps[:-self.single_obs_length]))
    else:
      self.override_past(obs)

  def reset(self):
    obs = self.env.reset()
    self.override_past(obs)
    return self.past_steps
  
  def step(self, action):
    s,r,d,i = self.env.step(action)
    self.shift_in(s)
    return self.past_steps,r,d,i
  
  def close(self):
    return self.env.close()

  def render(self):
    return self.env.render()
  

  