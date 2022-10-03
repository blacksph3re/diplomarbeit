import gym
import numpy as np

# Implements ipc as coleman transform of bending moments
class ColemanTransform(gym.Env):
  def __init__(self, env, hparams):
    self.env = env
    
    # How many degrees of IPC to do
    self.ipc_control_play = hparams.get_default('ipc_control_play', 3)

    # If no fixed phi lead, in which range to allow phi lead play
    self.variable_phi_lead_range = hparams.get_default('ipc_phi_lead_range', (-np.pi/4, np.pi/4))
    self.order = hparams.get_default('coleman_order', 1)
    self.highpass_tau = hparams.get_default('coleman_highpass_tau', 1/(0.2))
    self.action_sdq_factors = np.array(hparams.get_default('coleman_action_sdq_factors', [1.0,1.0,1.0]))

    self.coleman_s_to_obs = hparams.get_default('coleman_s_to_obs', True)

    # Reward-related things

    self.r_coleman_factor = hparams.get_default('reward_coleman_factor', None)
    self.r_coleman_norm = hparams.get_default('reward_coleman_norm', 2e-7)
    self.r_coleman_sdq_weights = np.array(hparams.get_default('reward_coleman_sdq_weights', [1,1,1]))

    if self.coleman_s_to_obs:
      assert len(self.r_coleman_sdq_weights) == 3
    else:
      assert len(self.r_coleman_sdq_weights) == 2

    self.r_coleman_action_factor = hparams.get_default('reward_coleman_action_factor', None)
    self.r_coleman_action_norm = hparams.get_default('reward_coleman_action_norm', 0.2)
    self.r_coleman_action_sdq_weights = np.array(hparams.get_default('reward_coleman_action_sdq_weights', [1,1,1]))

    self.r_constant_offset = hparams.get_default('reward_constant_offset', 1)

    self.r_clip = hparams.get_default('reward_clip', 5)

    self.action_space = gym.spaces.Box(
      low = np.array([env.action_space.low[0], -self.ipc_control_play, -self.ipc_control_play, -self.ipc_control_play, self.variable_phi_lead_range[0]]),
      high = np.array([env.action_space.high[0], self.ipc_control_play, self.ipc_control_play, self.ipc_control_play, self.variable_phi_lead_range[1]]),
      dtype = env.action_space.dtype
    )
    
    if self.coleman_s_to_obs:
      self.observation_space = gym.spaces.Box(
        low = np.concatenate([env.observation_space.low, np.array([-np.inf, -np.inf, -np.inf])]),
        high = np.concatenate([env.observation_space.high, np.array([np.inf, np.inf, np.inf])]),
        dtype = env.observation_space.dtype
      )
    else:
      self.observation_space = gym.spaces.Box(
        low = np.concatenate([env.observation_space.low, np.array([-np.inf, -np.inf])]),
        high = np.concatenate([env.observation_space.high, np.array([np.inf, np.inf])]),
        dtype = env.observation_space.dtype
      )

    self.metadata = env.metadata

    # Our env must have a last_info where we can read the last control proposal from
    # Walk back through the envs until we found the original client env
    self.clientenv = self.env
    while not hasattr(self.clientenv, "is_client_env") or not self.clientenv.is_client_env:
      assert self.clientenv.env, "no client env found!"
      self.clientenv = self.clientenv.env
    
    self.highpass_last_s = None
    self.highpass_last_filtered_s = None
    self.last_sdq = None

  
  def coleman_transf(self, azi,MY1,MY2,MY3):
    col_mat = 2.0/3*np.array([[0.5, 0.5, 0.5],
                              [np.cos(self.order*azi), np.cos(self.order*(azi+2*np.pi/3)), np.cos(self.order*(azi+4*np.pi/3))],
                              [np.sin(self.order*azi), np.sin(self.order*(azi+2*np.pi/3)), np.sin(self.order*(azi+4*np.pi/3))]])
    return np.dot(col_mat,np.array([MY1,MY2,MY3]))


  def inv_coleman_transf(self, azi,lead,SDQ):
    inv_col_mat = np.array([[1, np.cos(self.order*(azi+lead)), np.sin(self.order*(azi+lead))],
                            [1, np.cos(self.order*(azi+lead+2*np.pi/3)), np.sin(self.order*(azi+2*np.pi/3))],
                            [1, np.cos(self.order*(azi+lead+4*np.pi/3)), np.sin(self.order*(azi+lead+4*np.pi/3))]])

    return np.dot(inv_col_mat,SDQ)

  # def simple_reward(dq,offset,multip):
  #   return offset - multip*np.power(np.linalg.norm(dq),2)

  def high_pass_filter(self,x,x_1,y_1):
    dt = 0.1
    a1 = -1*(dt -2*self.highpass_tau)/(dt+2*self.highpass_tau)
    b0 = 2*self.highpass_tau/(dt+2*self.highpass_tau)
    b1 = -1*b0
    
    return a1*y_1 + b0*x + b1*x_1

  def transform_obs(self, obs):
    azi = np.deg2rad(self.clientenv.last_orig_state[29])
    MY1 = self.clientenv.last_orig_state[7]
    MY2 = self.clientenv.last_orig_state[8]
    MY3 = self.clientenv.last_orig_state[9]


    sdq = self.coleman_transf(azi, MY1, MY2, MY3)

    if not self.coleman_s_to_obs:
      return np.concatenate([obs, sdq[[1,2]]])

    # Make sure last highpass values are initialized
    self.highpass_last_s = self.highpass_last_s or sdq[0]
    self.highpass_last_filtered_s = self.highpass_last_filtered_s or 0

    # Highpass filter s
    filtered_s = self.high_pass_filter(sdq[0], self.highpass_last_s, self.highpass_last_filtered_s)

    self.highpass_last_s = sdq[0]
    self.highpass_last_filtered_s = filtered_s

    sdq[0] = filtered_s

    return np.concatenate([obs, sdq]), sdq

  def calc_reward(self, sdq, SDQ):
    coleman_reward = -self.r_coleman_factor * self.r_coleman_norm * np.linalg.norm(sdq * self.r_coleman_sdq_weights)

    coleman_action_reward = -self.r_coleman_action_factor * self.r_coleman_action_norm * np.linalg.norm(SDQ * self.r_coleman_action_sdq_weights)

    r = coleman_reward + coleman_action_reward + self.r_constant_offset
    r = np.clip(r, -self.r_clip, self.r_clip)

    i = {
      'coleman_reward': coleman_reward,
      'coleman_action_reward': coleman_action_reward,
      'constant_offset': self.r_constant_offset
    }

    return r, i

  def reset(self):
    self.highpass_last_s = None
    self.highpass_last_filtered_s = None
    s, sdq = self.transform_obs(self.env.reset())
    self.last_sdq = sdq
    return s
  
  def step(self, action):
    # Clip values outside of allowed range
    action = np.clip(action, self.action_space.low, self.action_space.high)

    SDQ = (action[1:4] * self.action_sdq_factors) / np.sqrt(2)
    phi_lead = action[4]
    azi = np.deg2rad(self.clientenv.last_orig_state[29])

    pitch_moments = self.inv_coleman_transf(azi, phi_lead, SDQ)

    action = np.array([action[0], pitch_moments[0], pitch_moments[1], pitch_moments[2]])

    # Add action to previous one
    action = self.clientenv.last_info['controller_action'] + action

    s,_,d,i = self.env.step(action)
    s, sdq = self.transform_obs(s)
    # Reward is calculated on the last timestep (s_t, a_t)
    # s is actually s_{t+1}
    r, i_reward = self.calc_reward(self.last_sdq, SDQ)
    self.last_sdq = sdq

    i['reward_composition'] = i_reward
    i['coleman'] = {
      's': sdq[0],
      'd': sdq[1],
      'q': sdq[2],
      'S': SDQ[0],
      'D': SDQ[1],
      'Q': SDQ[2],
      'phi_lead': phi_lead,
    }


    return s,r,d,i

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()