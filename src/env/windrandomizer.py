import gym
import numpy as np

# Randomizes wind parameters
class WindRandomizer(gym.Env):
  def __init__(self, env, hparams):
    self.env = env

    self.action_space = env.action_space
    self.observation_space = env.observation_space
    self.metadata = env.metadata

    self.inflow = 0
    self.speed = 0

    self.default_vertical_angle = 0
    self.default_shear_exponent = 0
    self.default_reference_height = 90

  def reset(self):
    self.speed = np.random.uniform(10.5, 11.5)
    self.inflow = np.random.uniform(-1, 1)
    #print("Running witn %f" % self.speed)

    self.env.setPowerLawWind(self.speed, self.inflow, self.default_vertical_angle, self.default_shear_exponent, self.default_reference_height)

    return self.env.reset()
  
  def step(self, action):
    self.inflow = np.clip(self.inflow + np.random.normal(0, 0.001), -1, 1)
    self.env.setPowerLawWind(self.speed, self.inflow, self.default_vertical_angle, self.default_shear_exponent, self.default_reference_height)
    
    return self.env.step(action)

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()