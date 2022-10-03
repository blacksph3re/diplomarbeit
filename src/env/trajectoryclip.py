import gym

class TrajectoryClip(gym.Env):
  def __init__(self, env, hparams):
    self.env = env
    
    self.metadata = env.metadata
    self.action_space = env.action_space
    self.observation_space = env.observation_space

    self.steps = 0
    self.max_length = hparams.get_default('max_trajectory_length', 2000)
    assert self.max_length > 0

    
  def step(self, action):
    s,r,d,i = self.env.step(action)

    self.steps += 1

    if self.steps >= self.max_length:
      d = True

    return s,r,d,i
  
  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()
  
  def reset(self):
    self.steps = 0
    return self.env.reset()

