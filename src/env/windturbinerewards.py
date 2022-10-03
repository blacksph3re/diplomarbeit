import gym
import numpy as np

class WindturbineRewards(gym.Env):
  def __init__(self, env, hparams):
    self.env = env
    
    self.metadata = env.metadata
    self.action_space = env.action_space
    self.observation_space = env.observation_space

    # There are several tasks implemented
    # Each task has a parameter and a factor
    # The parameter determines the value to be hold
    # The factor determines how much it counts into the total reward

    # Hold a rated speed
    self.hold_speed_parameter = hparams.get_default('reward_hold_speed_param', 0.9094)
    self.hold_speed_epsilon = hparams.get_default('reward_hold_speed_epsilon', 0.05)
    self.hold_speed_factor = hparams.get_default('reward_hold_speed_factor', 0.01)
    
    # Achieve maximum power
    self.max_power_factor = hparams.get_default('reward_max_power_factor', 0.1)
    self.max_power_norm = hparams.get_default('reward_max_power_norm', 1e-4)
    
    # Don't die
    self.death_factor = hparams.get_default('reward_death_factor', 500)
    
    # Don't exceed speed
    self.excess_speed_parameter = hparams.get_default('reward_max_speed_param', 1.2)
    self.excess_speed_factor = hparams.get_default('reward_max_speed_factor', 20)

    self.under_speed_parameter = hparams.get_default('reward_min_speed_param', 0.6)
    self.under_speed_factor = hparams.get_default('min_speed_factor', 10)

    # Don't exceed power
    self.excess_power_parameter = hparams.get_default('reward_excess_power_param', 10000)
    self.excess_power_factor = hparams.get_default('reward_excess_power_factor', 2)

    # Don't move pitch
    self.pitch_fluctuation_factor = hparams.get_default('reward_pitch_fluctuation', 18)

    # Don't move torque
    self.torque_fluctuation_factor = hparams.get_default('reward_torque_fluctuation', 4)

    # Don't wobble blades
    self.blade_bend_fluctuation_factor = hparams.get_default('reward_blade_bending', 2)
    # Quadratic penalty norms:
    # self.blade_bend_norm_connected = hparams.get_default('reward_blade_bend_norm_connected', 1e-14)
    # self.blade_bend_norm_individual = hparams.get_default('reward_blade_bend_norm_individual', 2e-13)

    self.blade_bend_norm_connected = hparams.get_default('reward_blade_bend_norm_connected', 1e-8)
    self.blade_bend_norm_individual = hparams.get_default('reward_blade_bend_norm_individual', 1e-8)
    self.average_blade_bendings = hparams.get_default('reward_blade_bending_mode', 'connected')
    self.blade_bend_history = hparams.get_default('reward_blade_moving_average_length', 5)

    # Minimize tower accelerations
    self.tower_bending_factor_x = hparams.get_default('reward_tower_bending_factor_x', 1) # Side-side
    self.tower_bending_factor_y = hparams.get_default('reward_tower_bending_factor_y', 0.5) # Fore-aft
    self.tower_bend_history = hparams.get_default('reward_tower_moving_average_length', 300)
    self.tower_bending_norm_x = hparams.get_default('reward_tower_bending_norm_x', 1e-8)
    self.tower_bending_norm_y = hparams.get_default('reward_tower_bending_norm_y', 1e-7)

    # Minimize coleman transformed dq
    self.coleman_factor = hparams.get_default('reward_coleman_factor', None)
    if self.coleman_factor:
      assert 'coleman_transform' in hparams and hparams['coleman_transform'] == True
    self.coleman_norm = hparams.get_default('reward_coleman_norm', 2e-7)
    self.coleman_sdq_weights = np.array(hparams.get_default('reward_coleman_sdq_weights', [1,1,1]))
    self.coleman_s_to_obs = 'coleman_s_to_obs' in hparams and hparams['coleman_s_to_obs']
    if self.coleman_s_to_obs:
      assert len(self.coleman_sdq_weights) == 3
    else:
      assert len(self.coleman_sdq_weights) == 2

    # Quadratic penalty norms:
    # self.tower_bending_norm_x = hparams.get_default('reward_tower_bending_norm_x', 3e-16)
    # self.tower_bending_norm_y = hparams.get_default('reward_tower_bending_norm_y', 3e-14)

    # How long to keep samples in the past for moving averages
    self.observation_history = max(self.tower_bend_history, self.blade_bend_history)

    # A bonus for surviving a timestep
    self.constant_offset = hparams.get_default('reward_constant_offset', 1)

    self.reward_clip = hparams.get_default('reward_clip', 5)

    # Store the last action to calculate torque/pitch fluctuation
    self.last_action = None
    
    # Store the last obs to calculate bending moment fluctuations
    self.last_observations = []

  def step(self, action):
    if self.last_action is None:
      self.last_action = action

    # TODO reward calculation should happen here, before the next step is done on the old state

    s, _, d, i = self.env.step(action)

    obshist = np.stack(self.last_observations)

    # s[0] is speed
    # s[1] is power


    # Observation space:
    # rpm, power, pitch, torque, bending moments, baseline controller actions

    # Action space:
    # Collective pitch, +-3 Grad zu baseline Controller Wert

    # Rewart
    # Extremlast bei Wurzel/Tower Biegemoment unter einem Wert, harte Penalty darüber
    # Integrierte abs power differenz zu rated minimieren
    # Integr. absoluter wert der Pitchgeschwingigkeiten minimieren

    # Die Turbine wird sich ausschalten, wenn Maximallasten überschritten werden (10% über rated)

    # Pipeline
    # Simulation -> Observation
    # Observation -> Baseline Controller -> Proposed Action
    # Observation <concat> Proposed Action -> RL Agent -> Delta Action
    # Delta Action + Proposed Action -> Simulation

    pitch_indices = [4,5,6]

    max_power = self.max_power_factor * s[1] * self.max_power_norm if s[1] < self.excess_power_parameter else self.max_power_factor * self.excess_power_parameter * self.max_power_norm
    hold_speed = -self.hold_speed_factor * np.abs((s[0] - self.hold_speed_parameter) / self.hold_speed_parameter) if np.abs(s[0] - self.hold_speed_parameter) > self.hold_speed_epsilon else 0
    death_penalty = -self.death_factor if d else 0
    excess_speed = (-self.excess_speed_factor * (s[0] - self.excess_speed_parameter) / self.excess_speed_parameter) if s[0] > self.excess_speed_parameter else 0
    under_speed = (-self.under_speed_factor * (self.under_speed_parameter - s[0]) / self.under_speed_parameter) if s[0] < self.under_speed_parameter else 0
    excess_power = (-self.excess_power_factor * (s[1] - self.excess_power_parameter) / self.excess_power_parameter) if s[1] > self.excess_power_parameter else 0
    torque_fluctuation = -self.torque_fluctuation_factor * (np.abs(self.last_observations[-1][31] - s[31])) / (self.action_space.high[0] - self.action_space.low[0])
    pitch_fluctuation = -self.pitch_fluctuation_factor * np.mean(np.abs(self.last_observations[-1][pitch_indices] - s[pitch_indices]))

    if self.average_blade_bendings == "connected":
      blade_bending = -self.blade_bend_fluctuation_factor * np.sum(np.abs(obshist[-self.blade_bend_history:,[7,8,9]].mean() - s[[7,8,9]])) * self.blade_bend_norm_connected
    else:
      blade_bending = -self.blade_bend_fluctuation_factor * np.sum(np.abs(obshist[-self.blade_bend_history:,[7,8,9]].mean(axis=0) - s[[7,8,9]])) * self.blade_bend_norm_individual
    #blade_bending = -self.blade_bend_fluctuation_factor * np.sum(np.abs(obshist[-1,[7,8,9]] - s[[7,8,9]]))
    tower_bending_x = -self.tower_bending_factor_x * np.abs(obshist[-self.tower_bend_history:,26].mean() - s[26]) * self.tower_bending_norm_x
    tower_bending_y = -self.tower_bending_factor_y * np.abs(obshist[-self.tower_bend_history:,27].mean() - s[27]) * self.tower_bending_norm_y

    coleman_reward = 0
    if self.coleman_factor:
      sdq = s[[42,43,44]] if self.coleman_s_to_obs else s[[42,43]]
      coleman_reward = -self.coleman_factor * self.coleman_norm * np.linalg.norm(sdq * self.coleman_sdq_weights)

    r = max_power + hold_speed + death_penalty + excess_speed + under_speed + excess_power + torque_fluctuation + pitch_fluctuation + self.constant_offset + blade_bending + tower_bending_x + tower_bending_y + coleman_reward

    r = np.clip(r, -self.reward_clip, self.reward_clip)

    i['reward_composition'] = {
      'max_power': max_power,
      'hold_speed': hold_speed,
      'death_penalty': death_penalty,
      'excess_speed': excess_speed,
      'under_speed': under_speed,
      'excess_power': excess_power,
      'torque_fluctuation': torque_fluctuation,
      'pitch_fluctuation': pitch_fluctuation,
      'constant_offset': self.constant_offset,
      'blade_bending': np.clip(blade_bending, -self.reward_clip, self.reward_clip),
      'tower_bending_x': np.clip(tower_bending_x, -self.reward_clip, self.reward_clip),
      'tower_bending_y': np.clip(tower_bending_y, -self.reward_clip, self.reward_clip),
      'coleman_reward': coleman_reward
    }
    i['orig_reward'] = r

    self.last_action = np.copy(action)
    self.last_observations.append(np.copy(s))
    if len(self.last_observations) > self.observation_history:
      self.last_observations.pop(0)
    return s, r, d, i


  def reset(self):
    self.last_action = None
    s = self.env.reset()
    self.last_observations = [np.copy(s)]
    return s
  
  def close(self):
    return self.env.close()

  def render(self):
    return self.env.render()