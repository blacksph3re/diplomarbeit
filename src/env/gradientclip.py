import gym
import numpy as np

# Clips the action gradients
class GradientClip(gym.Env):
  def __init__(self, env, hparams):
    self.env = env

    self.action_space = env.action_space
    self.observation_space = env.observation_space
    self.metadata = env.metadata

    # NREL 5MW
    # time_step = 0.1
    # gearbox_ratio = 97
    # torque_step = 15000
    # pitch_step = 8
    # yaw_step = 2

    # IEA 10MW
    time_step = 0.1
    gearbox_ratio = 1
    torque_step = 3.3e6
    pitch_step = 4
    yaw_step = 2

    self.threshold = np.array([
      torque_step * gearbox_ratio * time_step,
      yaw_step * time_step,
      pitch_step * time_step,
      pitch_step * time_step,
      pitch_step * time_step,
    ])

    if len(env.action_space.low) == 4:
      self.threshold = self.threshold[[0,2,3,4]]

    self.last_action = np.zeros(self.action_space.shape)

  def reset(self):
    res = self.env.reset()

    # Get last controller action, set that as default
    clientenv = self.env
    while not hasattr(clientenv, "last_info") or not clientenv.last_info:
      assert clientenv.env, "no client-env with last_info set found!"
      clientenv = clientenv.env

    self.last_action = clientenv.last_info['controller_action']
    return res
  
  def step(self, action):
    action_grads = action - self.last_action

    # Limit higher values
    indices = action_grads > self.threshold
    action[indices] = self.last_action[indices] + self.threshold[indices]

    # Limit lower values
    indices = action_grads < -self.threshold
    action[indices] = self.last_action[indices] - self.threshold[indices]

    self.last_action = action

    return self.env.step(action)

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()