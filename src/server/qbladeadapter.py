import ctypes
import _ctypes
import time
import numpy as np
import itertools
import os
import gym
import base64

# Turbsim : Binaries/TurbSim64
# Controller: ControllerFiles/
# QBlade needs to run on a separate folder for turbsim,
# as it's creating the windfield in a file, cwd is enough

# Basic qblade adapter
# Returns relatively raw qblade data

# the common order of execution would be:
#     createInstance
#     loadProject
#     addTurbulentWind
#     initializeSimulation
#     setPowerLawWind
#     for (int i=0;i<num;i++)
#     {
#     advanceStructure
#     setPowerLawWind
#     advanceAero
#     advanceController
#     getTurbineOperation
#     setControlVars
#     }
#     storeProject



class QBladeAdapter(gym.Env):
  def __init__(self, config):
    self.config = config
    self.project = config['qblade']['qblade_definition']

    self.qbladeLibFile = config['binaries']['qblade_library']
    self.turbulent_wind = config['qblade']['turbulent_wind']
    try:
      if config['binaries']['preload_chrono']:
        print("loading chrono library")
        ctypes.CDLL(config['binaries']['preload_chrono'])
    except Exception as e:
      print("Didn't preload chrono")
      print(e)

    self._qbladeLib = None
    print("loading qblade library")
    qbladeLib = ctypes.CDLL(self.qbladeLibFile)
    self._qbladeLib = qbladeLib
    self.map_functions(qbladeLib)


    print("creating qblade instance")
    load_start = time.time()
    self._createInstance()
    self.load_default_project()
    load_end = time.time()

    print("qblade init done (%fs)" % (load_end - load_start))

    self.yaw_control = config['qblade']['yaw_control']

    # NREL 5MW
    #gearbox_ratio = 97
    #generator_torque = 47402.91
    gearbox_ratio = config['qblade']['gearbox_ratio']
    generator_torque = config['qblade']['max_generator_torque']
    max_torque = generator_torque*gearbox_ratio
    max_blade_pitch = config['qblade']['max_blade_pitch']
    max_yaw = config['qblade']['max_yaw']

    if self.yaw_control:
      self.action_space = gym.spaces.Box(
        low = np.array([0.0,-max_yaw, 0.0, 0.0, 0.0]),
        high = np.array([max_torque, max_yaw, max_blade_pitch, max_blade_pitch, max_blade_pitch]),
        dtype = np.float64,
      )
    else:
      self.action_space = gym.spaces.Box(
        low = np.array([0.0, 0.0, 0.0, 0.0]),
        high = np.array([max_torque, max_blade_pitch, max_blade_pitch, max_blade_pitch]),
        dtype = np.float64,
      )

    # 38 Sensor measurements and 5 controller inputs
    obs_space = 38 + 5

    # Without yaw control we don't pass the yaw observation
    if not self.yaw_control:
      obs_space -= 1

    self.observation_space = gym.spaces.Box(
      low = -np.inf,
      high = np.inf,
      shape = (obs_space,),
      dtype = np.float64,
    )

    # Only generate these once, as I don't trust the garbage collection on ctypes
    self.out_data = (ctypes.c_double * 38)()
    self.in_data = (ctypes.c_double * 5)()
    self.controller_data = (ctypes.c_double * 5)()

    self.sim_started = False
    self.wind_info = {}

    self.log = []

  def map_functions(self, qbladeLib):
    self._createInstance = qbladeLib.createInstance
    self._initializeSimulation = qbladeLib.initializeSimulation
    self._initializeSimulation.argtypes = [ctypes.c_int, ctypes.c_int]
    self._loadProject = qbladeLib.loadProject
    self._loadProject.argtypes = [ctypes.c_char_p]
    self._storeProject = qbladeLib.storeProject
    self._storeProject.argtypes = [ctypes.c_char_p]
    self._loadSimDefinition = qbladeLib.loadSimDefinition
    self._loadSimDefinition.argtypes = [ctypes.c_char_p]
    self._addTurbulentWind = qbladeLib.addTurbulentWind
    self._addTurbulentWind.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.c_double,
      ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_bool]
    self._advanceAero = qbladeLib.advanceAero
    self._advanceController = qbladeLib.advanceController
    self._advanceController.argtypes = [ctypes.POINTER(ctypes.c_double)]
    self._advanceStructure = qbladeLib.advanceStructure
    self._getTurbineOperation = qbladeLib.getTurbineOperation
    self._getTurbineOperation.argtypes = [ctypes.POINTER(ctypes.c_double)]
    self._setPowerLawWind = qbladeLib.setPowerLawWind
    self._setPowerLawWind.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double]
    self._setControlVars = qbladeLib.setControlVars
    self._setControlVars.argtypes = [ctypes.POINTER(ctypes.c_double)]
    self._setTimestepSize = qbladeLib.setTimestepSize
    self._setTimestepSize.argtypes = [ctypes.c_double]
    self._setInitialConditions = qbladeLib.setInitialConditions
    self._setInitialConditions.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]



  def map_functions_decorated(self, qbladeLib):
    self._createInstance = qbladeLib._Z14createInstancev
    self._initializeSimulation = qbladeLib._Z20initializeSimulationii
    self._initializeSimulation.argtypes = [ctypes.c_int, ctypes.c_int]
    self._loadProject = qbladeLib._Z11loadProjectPc
    self._loadProject.argtypes = [ctypes.c_char_p]
    self._storeProject = qbladeLib._Z12storeProjectPc
    self._storeProject.argtypes = [ctypes.c_char_p]
    self._loadSimDefinition = qbladeLib._Z17loadSimDefinitionPc
    self._loadSimDefinition.argtypes = [ctypes.c_char_p]
    self._addTurbulentWind = qbladeLib._Z16addTurbulentWindddddiddPcS_idd
    self._addTurbulentWind.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.c_double,
      ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_double, ctypes.c_double]
    self._advanceAero = qbladeLib._Z11advanceAerov
    self._advanceController = qbladeLib._Z17advanceControllerPd
    self._advanceController.argtypes = [ctypes.POINTER(ctypes.c_double)]
    self._advanceStructure = qbladeLib._Z16advanceStructurev
    self._getTurbineOperation = qbladeLib._Z19getTurbineOperationPd
    self._getTurbineOperation.argtypes = [ctypes.POINTER(ctypes.c_double)]
    self._setPowerLawWind = qbladeLib._Z15setPowerLawWindddddd
    self._setPowerLawWind.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double]
    self._setControlVars = qbladeLib._Z14setControlVarsPd
    self._setControlVars.argtypes = [ctypes.POINTER(ctypes.c_double)]
    self._setTimestepSize = qbladeLib._Z15setTimestepSized
    self._setTimestepSize.argtypes = [ctypes.c_double]
  
  def reset_pitch_actuator_model(self, observation):
    self.pitch_actuator_state = []

    for blade in [0,1,2]:
      self.pitch_actuator_state.append({
        'x': observation[4+blade],
        'x-1': observation[4+blade],
        'x-2': observation[4+blade],
        'y-1': 0,
        'y-2': 0,
      })

  # Pitch actuator model
  def pitch_actuator_model(self, action):
    # The pitch actuator model needs to be enabled explicitely
    if not self.config['qblade'].get('pitch_actuator_model', False):
      return action

    action_offset = 2 if self.yaw_control else 1

    for blade in [0,1,2]:
      y = self.low_pass_filter(action[action_offset+blade],
                               self.pitch_actuator_state[blade]['x-1'],
                               self.pitch_actuator_state[blade]['x-2'],
                               self.pitch_actuator_state[blade]['y-1'],
                               self.pitch_actuator_state[blade]['y-2'])
      
      self.pitch_actuator_state[blade]['x-2'] = self.pitch_actuator_state[blade]['x-1']
      self.pitch_actuator_state[blade]['x-1'] = action[action_offset+blade]
      self.pitch_actuator_state[blade]['y-2'] = self.pitch_actuator_state[blade]['y-1']
      self.pitch_actuator_state[blade]['y-1'] = y
      action[action_offset+blade] = y
    return action

  def low_pass_filter(self, x,x_1,x_2,y_1,y_2,dt=0.1,omega=2,xi=0.7):
    # freq. in rad/s
    omega = 2*np.pi*omega  

    d = 3 + 3*xi*omega*dt + omega**2*dt**2
    a1 = (6-omega**2*dt**2)/d
    a2 = (-3 + 3*xi*omega*dt - omega**2*dt**2)/d
    b0 = (omega**2*dt**2)/d
    b1 = b0
    b2 = b0

    return a1*y_1 + a2*y_2 + b0*x + b1*x_1 + b2*x_2


  def random_value(self, prefix):
    category = self.config['qblade'][prefix + '_type']
    value = self.config['qblade'][prefix + '_value']

    if category == 'const':
      return value
    if category == 'uniform':
      return np.random.uniform(float(value[0]), float(value[1]))
    if category == 'choice':
      return np.random.choice([x for x in value])

  def load_default_project(self):
    print("loading qblade project")
    self.loadDefinition(self.project)
    self.steps_since_reload = 0

  def apply_wind_info(self, wind_info):
    if self.turbulent_wind:
      # Create turbulent wind
      # //This function allows to define and add a turbulent windfield to the simulations,m if a turbulent windfield is used the function 'setPowerLawWind' has no effect
      # //windspeed: the mean windspeed at the reference height
      # //refheight: the reference height
      # //hubheight: the hubheight, more specifically the height of the windfield center
      # //dimensions: the y- and z- dimensions of the windfield in meters
      # //gridpoints: the number of points in the y and z direction for which velocities are evaluated
      # //length: the simulated length of the windfield in seconds
      # //dT: the temporal resolution of the windfield
      # //turbulenceClass: the turbulence class, can be "A", "B" or "C"
      # //turbulenceType: the turbulence type, can be "NTM", "ETM", "xEWM1" or "xEWM50" - where x is the turbine class (1,2 or 3)
      # //seed: the random seed for the turbulent windfield
      # //vertInf: vertical inflow angle in degrees
      # //horInf: horizontal inflow angle in degrees
      # //removeFiles: remove files after processing

      self._addTurbulentWind(
        ctypes.c_double(self.wind_info["windspeed"]),
        ctypes.c_double(119.6),
        ctypes.c_double(119.6),
        ctypes.c_double(210.0),
        ctypes.c_int(20),
        ctypes.c_double(350.0),
        ctypes.c_double(0.1),
        ctypes.create_string_buffer(bytes(self.wind_info['turbulence_class'], 'utf-8')),
        ctypes.create_string_buffer(bytes(self.wind_info['turbulence_type'], 'utf-8')),
        ctypes.c_int(self.wind_info["wind_rng_seed"]),
        ctypes.c_double(self.wind_info["inflow_angle_hor"]),
        ctypes.c_double(self.wind_info["inflow_angle_vert"]),
        ctypes.c_bool(True),
      )
    else:
      self._setPowerLawWind(
        ctypes.c_double(self.wind_info["windspeed"]),
        ctypes.c_double(self.wind_info["inflow_angle_hor"]),
        ctypes.c_double(0),
        ctypes.c_double(0.2),
        ctypes.c_double(119.6))
    
    self._setInitialConditions(ctypes.c_double(0), ctypes.c_double(0), ctypes.c_double(self.wind_info["init_rotor_azimuth"]))

  def reset(self, wind_info=None):
    try:
      os.remove('turbsim.inp')
      os.remove('turbsim.bts')
      os.remove('turbsim.sum')
    except:
      pass
    try:
      os.remove('windfield.inp')
      os.remove('windfield.bts')
      os.remove('windfield.sum')
    except:
      pass

    print('Resetting simulation')
    #self.load_default_project()
    self.log = []

    # Create a wind field
    if wind_info:
      self.wind_info = wind_info
    else:
      np.random.seed(int.from_bytes(os.urandom(4), byteorder='big'))
      self.wind_info = {
        "inflow_angle_hor": float(self.random_value('inflow_angle_hor')),
        "inflow_angle_vert": float(self.random_value('inflow_angle_vert')),
        "wind_rng_seed": int(self.random_value('rng_seed')),
        "windspeed": float(self.random_value('windspeed')),
        "init_rotor_azimuth": float(self.random_value('init_rotor_azimuth')),
        "turbulence_class": self.random_value('turbulence_class'),
        "turbulence_type": self.random_value('turbulence_type'),
        "turbulent": self.turbulent_wind
      }

      assert self.wind_info['turbulence_class'] in ['A', 'B', 'C']
      assert self.wind_info['turbulence_type'] in ['NTM', 'ETM', '1EWM1', '2EWM1', '3EWM1', '1EWM50', '2EWM50', '3EWM50']
    
    time_wind = time.time()
    self.apply_wind_info(self.wind_info)
    
    time_init = time.time()
    self._initializeSimulation(ctypes.c_int(0), ctypes.c_int(32))
    time_struct = time.time()
    

    self._advanceStructure()
    time_aero = time.time()
    self._advanceAero()

    time_cont = time.time()
    
    state_history = []
    controller_action = self.extractController()
    laststate = self.extractObservation()
    self.reset_pitch_actuator_model(laststate)
    controller_action = self.pitch_actuator_model(controller_action)
    self.sim_started = False


    starttime = time.time()

    print('Init done (%f wind, %f init, %f struct, %f aero, %f cont), balancing simulation' % (time_init - time_wind, time_struct - time_init, time_aero - time_struct, time_cont - time_aero, starttime - time_cont))

    compute_struct = 0
    compute_aero = 0
    compute_cont = 0

    balance_iters = int(self.config['qblade']['balance_iters'])
    for _ in range(0, balance_iters):
      state_history.append(laststate)
      laststate,r,d,i = self.step(controller_action)
      controller_action = i["controller_action"]

      compute_struct += i["compute_time_structure"]
      compute_aero += i["compute_time_aero"]
      compute_cont += i["compute_time_controller"]
    elapsed = time.time() - starttime


    print('Balancing done, %f it/s (%f struct, %f aero, %f cont)' % (balance_iters/elapsed, compute_struct/balance_iters, compute_aero/balance_iters, compute_cont/balance_iters))

    self.log = []
    self.log.append(("reset", self.wind_info))
    info = {
      "controller_action": controller_action,
      "wind_info": self.wind_info,
      "log": self.log,
      "balance_history": state_history,
    }

    return np.nan_to_num(laststate), info


  def calc_reward(self, observation):
    # Here, only calc a very basic reward
    rated_power = 5000
    return -np.abs((observation[1]-rated_power)/rated_power)
    
  def calc_death(self, observation):
    # If there are nan values, reload completely
    if(np.any(np.isnan(observation))):
      print('NaN values in observation!', observation)
      self.steps_since_reload += 100000
      return True

    if observation[0] < 0:
      return True

    # Other death calculations are done in client
    return False

  def storeAction(self, action):

    # Copy action to control vars
    action = np.clip(action, self.action_space.low, self.action_space.high)
    assert(not np.any(np.isnan(action)))

    if not self.yaw_control:
      action = np.insert(action, 1, 0)

    assert len(action) == 5

    for i in range(0, len(action)):
      self.in_data[i] = action[i]

    self._setControlVars(self.in_data)

  def extractObservation(self):
    # 38 values are hardcoded in the library
    # //vars[0] = rotational speed [rad/s]
    # //vars[1] = power [W]
    # //vars[2] = HH wind velocity [m/s]
    # //vars[3] = yag angle [deg]
    # //vars[4] = pitch blade 1 [deg]
    # //vars[5] = pitch blade 2 [deg]
    # //vars[6] = pitch blade 3 [deg]
    # //vars[7] = oop blade root bending moment blade 1 [N]
    # //vars[8] = oop blade root bending moment blade 2 [N]
    # //vars[9] = oop blade root bending moment blade 3 [N]
    # //vars[10] = ip blade root bending moment blade 1 [N]
    # //vars[11] = ip blade root bending moment blade 2 [N]
    # //vars[12] = ip blade root bending moment blade 3 [N]
    # //vars[13] = tor blade root bending moment blade 1 [Nm]
    # //vars[14] = tor blade root bending moment blade 2 [Nm]
    # //vars[15] = tor blade root bending moment blade 3 [Nm]
    # //vars[16] = oop tip deflection blade 1 [m]
    # //vars[17] = oop tip deflection blade 2 [m]
    # //vars[18] = oop tip deflection blade 3 [m]
    # //vars[19] = ip tip deflection blade 1 [m]
    # //vars[20] = ip tip deflection blade 2 [m]
    # //vars[21] = ip tip deflection blade 3 [m]
    # //vars[22] = tower top acceleration in global X [m^2/s]
    # //vars[23] = tower top acceleration in global Y [m^2/s]
    # //vars[24] = tower top acceleration in global Z [m^2/s]
    # //vars[25] = tower bottom bending moment along global X [Nm]
    # //vars[26] = tower bottom bending moment along global Y [Nm]
    # //vars[27] = tower bottom bending moment along global Z [Nm]
    # //vars[28] = current time [s]
    # //vars[29] = azimuthal position of the LSS [deg]
    # //vars[30] = azimuthal position of the HSS [deg]
    # //vars[31] = HSS torque [Nm]
    # //vars[32] = wind speed at hub height [m/s]
    # //vars[33] = horizontal inflow angle [deg]
    # //vars[34] = tower top fore aft acceleration [m/s^2]
    # //vars[35] = tower top side side acceleration [m/s^2]
    # //vars[36] = tower top X position [m]
    # //vars[37] = tower top Y position [m]
    self._getTurbineOperation(self.out_data)
    observation = [self.out_data[i] for i in range(0, 38)]

    return np.array(observation)
  
  def extractController(self):
    self._advanceController(self.controller_data)
    controller_action = np.array([self.controller_data[i] for i in range(0, 5)])

    if not self.yaw_control:
      controller_action = controller_action[[0,2,3,4]]

    return controller_action

  def step(self, action):
    self.steps_since_reload += 1
    self.sim_started = True
    self.log.append(("act", action))
    start = time.time()

    action = self.pitch_actuator_model(action)

    self.storeAction(action)

    poststore = time.time()

    self._advanceStructure()
    poststruc = time.time()
    self._advanceAero()
    postaero = time.time()
    controller_action = self.extractController()
    postcontroller = time.time()

    observation = self.extractObservation()

    death = self.calc_death(observation)
    observation = np.nan_to_num(observation)
    reward = self.calc_reward(observation)
    info = {
      "controller_action": controller_action,
      "wind_info": self.wind_info,
      "compute_time_structure": poststruc - poststore,
      "compute_time_aero": postaero - poststruc,
      "compute_time_controller": postcontroller - postaero,
      "compute_time": time.time() - start
    }

    return np.concatenate([observation, controller_action]), reward, death, info

  def render(self):
    pass

  def close(self):
    del self._qbladeLib

  def storeProject(self, filename):
    x = ctypes.c_char_p(bytes(filename, 'utf-8'))
    self._storeProject(x)

  def loadProject(self, filename):
    x = ctypes.c_char_p(bytes(filename, 'utf-8'))
    self._loadProject(x)

  def loadDefinition(self, filename):
    x = ctypes.c_char_p(bytes(filename, 'utf-8'))
    self._loadSimDefinition(x)
  
  
  def rollout_log(self, log):
    # Reset
    assert log[0][0] == "reset", "log did not start with reset"
    self.reset(wind_info=log[0][1])
    del log[0]

    # Step through the log
    for (t, d) in log:
      if t == "wind":
        self.apply_wind_info(d)
      elif t == "act":
        self.step(d)

    self.log = log
