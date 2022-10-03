import gym
import numpy as np 

class MeanNormalizer(gym.Env):
  def __init__(self, env, hparams):
    self.env = env

    self.metadata = env.metadata

    # Whether to clip observations to [-5,5]
    self.clip_obs = hparams.get_default('norm_clip_observations', False)
    self.clip_reward = hparams.get_default('norm_clip_rewards', False)
    self.norm_obs_active = hparams.get_default('normalize_observations', True)
    self.norm_act_active = hparams.get_default('normalize_actions', True)
    self.norm_reward_active = hparams.get_default('normalize_rewards', False)
    self.obs_mean_target = hparams.get_default('normalize_obs_to_mean', 0)
    self.obs_std_target = hparams.get_default('normalize_obs_to_std', 1)
    self.reward_mean_target = hparams.get_default('normalize_reward_to_mean', 0)
    self.reward_std_target = hparams.get_default('normalize_reward_to_std', 1)
    

    # For IAE 10MW
    self.state_mean = np.array([8.81474488e-01, 9.98063890e+03, 1.30495765e+01,-3.05708962e-17,
                                7.16200360e+00, 7.16200360e+00, 7.16200360e+00, 2.27661632e+07,
                                2.27661632e+07, 2.27661632e+07, 3.83974558e+06, 3.83974558e+06,
                                3.83974558e+06, 6.52965504e+04, 6.52965504e+04, 6.52965504e+04,
                                1.08416867e+01, 1.08416867e+01, 1.08416867e+01, 2.47745467e-01,
                                2.47745467e-01, 2.47745467e-01, 2.53458189e-04, 1.13170138e-04,
                                -2.30401181e-06,1.59962563e+07, 7.97358050e+07, 4.76085772e+05,
                                2.00119994e+02, 1.79677420e+02, 1.79677420e+02, 1.21506570e+07,
                                1.30495765e+01, 1.60031990e+00, 3.90643013e-04, 1.92217286e-04,
                                1.79641850e-01,-1.06182736e-01, 1.21539878e+07, 6.25790658e+00,
                                6.25790658e+00, 6.25790658e+00])

    self.state_std = np.array([ 7.89356443e-02, 4.06711684e+02, 4.97920461e-01, 1.86950790e-14,
                                2.40130531e+00, 2.40130531e+00, 2.40130531e+00, 5.28148900e+06,
                                5.28148900e+06, 5.28148900e+06, 9.62613962e+06, 9.62613962e+06,
                                9.62613962e+06, 4.86309051e+05, 4.86309051e+05, 4.86309051e+05,
                                2.98127533e+00, 2.98127533e+00, 2.98127533e+00, 2.95355851e-01,
                                2.95355851e-01, 2.95355851e-01, 2.02582659e-01, 1.85537934e-01,
                                2.36966358e-02, 2.24429867e+07, 3.65411401e+07, 5.97802786e+06,
                                5.77523506e+01, 1.03878388e+02, 1.03878388e+02, 1.28365436e+06,
                                4.97920461e-01, 5.98667318e+00, 2.01527937e-01, 1.85528585e-01,
                                1.58383411e-01, 9.16855308e-02, 1.35982137e+06, 3.20455298e+00,
                                3.20455298e+00, 3.20455298e+00])
    
    if 'coleman_transform' in hparams and hparams['coleman_transform']:
      self.state_mean = np.append(self.state_mean, np.array([6.47613371e+05, 2.28546739e+05]))
      self.state_std = np.append(self.state_std, np.array([2.84770330e+06, 3.15280344e+06]))

      if 'coleman_s_to_obs' in hparams and hparams['coleman_s_to_obs']:
        self.state_mean = np.append(self.state_mean, np.array([2.99850374e+05]))
        self.state_std = np.append(self.state_std, np.array([3.53680319e+06]))

    if 'polar_transform' in hparams and 'polar_transform_lss' in hparams and hparams['polar_transform_lss']:
      self.state_mean = np.append(self.state_mean, np.array([0,0]))
      self.state_std = np.append(self.state_std, np.array([0.7,0.7]))
    
    if 'polar_transform' in hparams and 'polar_transform_hss' in hparams and hparams['polar_transform_hss']:
      self.state_mean = np.append(self.state_mean, np.array([0,0]))
      self.state_std = np.append(self.state_std, np.array([0.7,0.7]))
    
    self.reward_mean = 0
    self.reward_std = 1


    self.observation_space = env.observation_space

    assert len(self.observation_space.low) == len(self.state_mean)
    assert len(self.observation_space.low) == len(self.state_std)

    self.old_action_space = env.action_space
    self.action_space = gym.spaces.Box(
      low = -np.ones(env.action_space.shape),
      high = np.ones(env.action_space.shape),
      dtype = env.action_space.dtype
    )

    # y = mx + c
    # y1 = mx1 + c
    # y2 = mx2 + c
    # y1 - y2 = mx1 - mx2
    # y1 - y2 = m(x1 - x2)
    # (y1 - y2)/(x1 - x2) = m
    # y - mx = c
    # self.act_m = (old_action_space.low - old_action_space.high) / (self.action_space.low - self.action_space.high) 
    # self.act_c = old_action_space.low - self.act_m * (self.action_space.low)
    
    # Under the assumption of a symmetric action space (as with differential control), denormalization is easy, just multiply
    if not np.allclose(self.old_action_space.low, -self.old_action_space.high):
      print('Warning: action space not symmetric: %s vs %s' % (str(self.old_action_space.low), str(self.old_action_space.high)))


  def norm_obs(self, obs):
    if not self.norm_obs_active:
      return obs

    obs = (obs - self.state_mean) / self.state_std
    obs = (obs * self.obs_std_target) + self.obs_mean_target
    if self.clip_obs:
      obs = np.clip(obs, -self.clip_obs, self.clip_obs)
    return obs

  def norm_reward(self, reward):
    if not self.norm_reward_active:
      return reward
    
    reward = (reward - self.reward_mean) / self.reward_std
    reward = (reward * self.reward_std_target) + self.reward_mean_target
    if self.clip_reward:
      reward = np.clip(reward, -self.clip_reward, self.clip_reward)
    return reward
  
  def denorm_act(self, act):
    if not self.norm_act_active:
      return act

    # act = act * self.act_m + self.act_c
    act = act * self.old_action_space.high
    return act

  def reset(self):
    return self.norm_obs(self.env.reset())
  
  def step(self, action):
    s,r,d,i = self.env.step(self.denorm_act(np.array(action)))
    return self.norm_obs(s),self.norm_reward(r),d,i
  
  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()
