import gym
import numpy as np
import torch
from pyts.image import GramianAngularField


# Includes a pre-trained extreme load classifier
class ExtremeLoadClassifier(gym.Env):
  def __init__(self, env, hparams):
    self.env = env
    self.metadata = env.metadata
    self.action_space = env.action_space

    self.observation_space = gym.spaces.Box(
      low = np.concatenate([env.observation_space.low, np.array([-np.inf, -np.inf, -np.inf])]),
      high = np.concatenate([env.observation_space.high, np.array([np.inf, np.inf, np.inf])]),
      dtype = env.observation_space.dtype
    )

    # Where to load the checkpoint
    checkpoint_path = hparams.get_default('elc_checkpoint', 'checkpoint.pth')
    self.softmax_temperature = hparams.get_default('elc_softmax_temperature', 5.0)
    
    checkpoint = torch.load(checkpoint_path, map_location=torch.device('cpu'))
    self.lookback_len = checkpoint['hparams']['lookback_len']
    self.mean = checkpoint['statistics']['mean']
    self.std = checkpoint['statistics']['std']
    self.model = checkpoint['model'].float().eval()

    if hparams.get_default('elc_uniform_classes', True):
      self.classes = np.array(range(len(checkpoint['hparams']['classes']))) / (len(checkpoint['hparams']['classes']) - 1)
    else:
      self.classes = np.array(checkpoint['hparams']['classes'])


    self.transformer = GramianAngularField(image_size=lookback_len, sample_range=None)

    # Our env must have a last_info where we can read the last control proposal from
    # Walk back through the envs until we found the original client env
    self.clientenv = self.env
    while not hasattr(self.clientenv, "is_client_env") or not self.clientenv.is_client_env:
      assert self.clientenv.env, "no client env found!"
      self.clientenv = self.clientenv.env

    self.state_history = []

  # Perform nn inference from the pretrained classifier
  def inference(s):
    self.state_history.append(self.clientenv.last_orig_state[[7,8,9]])
    self.state_history = self.state_history[-self.lookback_len:]
    
    data = np.array(self.state_history)
    data = np.clip((data - self.mean) / (2*self.std), -1, 1)
    data = self.transformer.transform(data.transpose())
    data = np.stack([
      data, data[[1,2,0]], data[[2,0,1]]
    ])
    with torch.no_grad():
      data = self.model(torch.tensor(data).float())
    # Multiply the class labels to the softmax and sum to get an averaged label per blade
    data = torch.nn.functional.softmax(data/self.softmax_temperature, dim=1).numpy() * self.classes
    data = data.sum(axis=1)

    return np.concatenate([s, data])
    
  def reset(self):
    s = self.env.reset()

    self.state_history = [x[[7,8,9]] for x in self.clientenv.balancing_log['balance_history']]
    s = self.inference(s)
    return s
  
  def step(self, action):
    s,r,d,i = self.env.step(action)

    s = self.inference(s)
 
    return s,r,d,i

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()