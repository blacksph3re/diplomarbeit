import gym
import numpy as np

# Implements differentiable control towards the baseline controller
class DifferentialControl(gym.Env):
  def __init__(self, env, hparams):
    self.env = env

    previous_space = env.action_space.high - env.action_space.low
    
    # +-10% control play is allowed
    factor = hparams.get_default('differential_control_play', 0.1)

    self.action_space = gym.spaces.Box(
      low = -previous_space*factor,
      high = previous_space*factor,
      dtype = env.action_space.dtype,
    )
    self.observation_space = env.observation_space
    self.metadata = env.metadata

  def reset(self):
    return self.env.reset()
  
  def step(self, action):
    # Our env must have a last_info where we can read the last control proposal from
    # Walk back through the envs until we found the original client env
    clientenv = self.env
    while not hasattr(clientenv, "last_info") or not clientenv.last_info:
      assert clientenv.env, "no client-env with last_info set found!"
      clientenv = clientenv.env

    # Clip values outside of allowed range
    action = np.clip(action, self.action_space.low, self.action_space.high)

    # Add action to previous one
    action = clientenv.last_info['controller_action'] + action

    return self.env.step(action)

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()