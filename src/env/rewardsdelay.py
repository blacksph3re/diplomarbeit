import gym

class RewardsDelay(gym.Env):
  def __init__(self, env):
    self.env = env
    
    self.metadata = env.metadata
    self.action_space = env.action_space
    self.observation_space = env.observation_space

    self.cumulative_reward = 0

    
  def step(self, action):
    s,r,d,i = self.env.step(action)

    self.cumulative_reward += r
    r = self.cumulative_reward if d else 0

    return s,r,d,i
  
  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()
  
  def reset(self):
    self.cumulative_reward = 0
    return self.env.reset()

