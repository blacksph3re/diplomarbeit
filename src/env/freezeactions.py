import gym
import numpy as np

# Adds two more actions which freeze the other actions when above 0.5
class FreezeActions(gym.Env):
  def __init__(self, env, hparams):
    self.env = env

    if len(env.action_space.low) == 2:
      self.collective_pitch = True
    elif len(env.action_space.low) == 4:
      self.collective_pitch = False
    else:
      raise "Freeze Actions can only be used after masking"

    self.action_space = gym.spaces.Box(
      low = np.concatenate((env.action_space.low, [0, 0])),
      high = np.concatenate((env.action_space.high, [1, 1])),
      dtype = env.action_space.dtype,
    )
    self.observation_space = env.observation_space
    self.metadata = env.metadata

    self.last_action = np.zeros(self.action_space.shape)

  def reset(self):
    self.last_action = np.zeros(self.action_space.shape)
    return self.env.reset()
  
  def step(self, action):
    # Change pitch/torque only when last two actions are greater than 0.5
    change_pitch = action[-1] > 0.5
    change_torque = action[-2] > 0.5
    
    # Copy last torque
    if not change_torque:
      action[0] = self.last_action[0]

    # Copy last pitch
    if not change_pitch:
      if self.collective_pitch:
        action[1] = self.last_action[1]
      else:
        action[1] = self.last_action[1]
        action[2] = self.last_action[2]
        action[3] = self.last_action[3]

    self.last_action = action

    return self.env.step(action[:-2])

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()