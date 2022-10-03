import gym
import numpy as np

# This past feeder applies an exponential dilation
# Steps are averaged like
# 01222333334444444555555555
# this 26 timesteps would be merged into 5 by averaging to the respective array index

class DilatedPastfeeder(gym.Env):
  def __init__(self, env, hparams):
    self.env = env

    self.metadata = env.metadata

    self.action_space = env.action_space
    
    self.past_feeding_steps = hparams.get_default('dilated_past_feeding_steps', 6)
    self.mask = np.concatenate([np.array([0])] + [np.ones(2*i+1)*(i+1) for i in range(self.past_feeding_steps-1)])
    

    self.observation_space = gym.spaces.Box(
      low = np.concatenate(tuple([env.observation_space.low for _ in range(0, self.past_feeding_steps)])),
      high = np.concatenate(tuple([env.observation_space.high for _ in range(0, self.past_feeding_steps)])),
      dtype = env.observation_space.dtype,
    )

    self.single_obs_length = env.observation_space.shape[0]

    self.buffer = np.array([[]])
  
  def override_past(self, obs):
    assert len(obs) == self.single_obs_length, "Obs length: %d, should be %d" % (len(obs), self.single_obs_length)
    self.buffer = np.stack([obs for _ in range(len(self.mask))])
  
  def shift_in(self, obs):
    # Check for the correct length
    assert(len(self.buffer) == len(self.mask))
      
    self.buffer = np.concatenate((np.expand_dims(obs, axis=0), self.buffer[:-1]), axis=0)

  
  def calculate_past(self):
    assert len(self.buffer) == len(self.mask)

    # Average all samples that are masked with the same number
    # If the mask was 2 2 3 3 3 then mean(buffer[[0,1]]) ++ mean(buffer[[2,3,4]])
    past = [np.mean(self.buffer[self.mask == i], axis=0) for i in range(self.past_feeding_steps)]

    # Flatten out the past observations
    retval = np.concatenate(past)
    assert len(retval) == self.past_feeding_steps * self.single_obs_length, "Length of concatenated samples wrong (%d seen, %d expected)" % (len(retval), self.past_feeding_steps * self.single_obs_length)
    return retval

  def reset(self):
    obs = self.env.reset()
    self.override_past(obs)
    return self.calculate_past()
  
  def step(self, action):
    s,r,d,i = self.env.step(action)
    self.shift_in(s)
    return self.calculate_past(),r,d,i
  
  def close(self):
    return self.env.close()

  def render(self):
    return self.env.render()
  

  