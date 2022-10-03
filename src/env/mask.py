import gym
import numpy as np

class Mask(gym.Env):
  def __init__(self, env, hparams=None):
    self.env = env

    self.metadata = env.metadata

    self.crop_obs_to = hparams.get_default('mask_obs', [0,1,4,5,6,7,8,9,26,27,42,43])
    if self.crop_obs_to is None:
      self.crop_obs_to = list(range(env.observation_space.shape[0]))
      hparams['mask_obs'] = self.crop_obs_to

    self.act_masking = hparams.get_default('mask_act', 'individual-pitch')
    self.fixed_phi_lead = hparams.get_default('ipc_fixed_phi_lead', 0.51836)

    if self.act_masking.startswith('coleman'):
      assert hparams['coleman_transform'] == True


    if self.act_masking == "collective-pitch":
      self.crop_act_to = [0,1]
    elif self.act_masking == "individual-pitch-no-torque":
      self.crop_act_to = [1,2,3]
    elif self.act_masking == "individual-pitch":
      self.crop_act_to = [0,1,2,3]
    elif self.act_masking == "coleman":
      self.crop_act_to = [0,1,2,3] if self.fixed_phi_lead else [0,1,2,3,4]
    elif self.act_masking == "coleman-no-torque":
      self.crop_act_to = [2,3] if self.fixed_phi_lead else [2,3,4]
    elif self.act_masking == "coleman-no-torque-s":
      self.crop_act_to = [1,2,3] if self.fixed_phi_lead else [1,2,3,4]
    else:
      raise NotImplementedError("Invalid act masking option: " + self.act_masking)
      
    hparams['mask_act_parsed'] = self.crop_act_to

    assert np.all([x < len(self.env.observation_space.low) for x in self.crop_obs_to])

    self.action_space = gym.spaces.Box(
      low = env.action_space.low[self.crop_act_to],
      high = env.action_space.high[self.crop_act_to],
      dtype = env.action_space.dtype,
    )
    self.observation_space = gym.spaces.Box(
      low = env.observation_space.low[self.crop_obs_to],
      high = env.observation_space.high[self.crop_obs_to],
      dtype = env.observation_space.dtype,
    )
  
  def mask_obs(self, obs):
    return np.array(obs)[self.crop_obs_to]
  
  def mask_action(self, act):
    if self.act_masking.startswith('coleman'):
      tmp_act = np.array([0, 0, np.nan, np.nan, self.fixed_phi_lead or act[-1]])

      if not self.fixed_phi_lead:
        act = act[:-1]

      if self.act_masking == 'coleman-no-torque':
        tmp_act[[2,3]] = act
      elif self.act_masking == 'coleman-no-torque-s':
        tmp_act[[1,2,3]] = act
      else:
        raise NotImplementedError('Invalid act masking %s' % self.act_masking)

      return tmp_act

    elif self.act_masking == 'collective_pitch':
      return np.array([act[0], act[1], act[1], act[1]])
    elif self.act_masking == 'individual-pitch-no-torque':
      return np.array([0, act[0], act[1], act[2]])
    return act[self.crop_act_to]

  def reset(self):
    return self.mask_obs(self.env.reset())

  def step(self, action):
    action = self.mask_action(action)

    s,r,d,i = self.env.step(action)

    return self.mask_obs(s), r, d, i

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()