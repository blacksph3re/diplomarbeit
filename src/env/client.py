import gym
import zmq
import pickle
import numpy as np
import io
import PIL
import pandas as pd
import matplotlib.pyplot as plt
import time
import sys
import os
import socket
import traceback


try:
  cur_path = os.path.dirname(os.path.abspath(__file__))
except:
  cur_path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(1, '%s/messages/python' % (os.getenv('BUILD_DIR') or os.path.abspath('%s/../../build' % cur_path)))
from agent_env_pb2 import AgentEnv, EnvAgent
from agent_broker_pb2 import RequestEnv, AssignEnv

class Client(gym.Env):
  def __init__(self, hparams):
    self._reset_client_vars()
    self._set_spaces()
    self.env_broker_address = hparams.get_default('env_broker_address', 'tcp://localhost:4749')
    self.env_config_group = hparams.get_default('env_config_group', 0)

  def _reset_client_vars(self):
    self.socket = None
    self.action_history = []

    self.last_info = None
    self.last_orig_state = None
    self.broker_socket = None
    self.context = None
    self.load_before_next_step = None
    self.balancing_log = None

    self.is_client_env = True

    self.context = zmq.Context.instance()
    self.hostname = socket.gethostname()


  def _set_spaces(self):
    yaw_control = False
    gearbox_ratio = 1
    generator_torque = 15.6e+06
    max_torque = generator_torque*gearbox_ratio
    max_blade_pitch = 90.0
    max_yaw = 90.0

    if yaw_control:
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
    if not yaw_control:
      obs_space -= 1

    self.observation_space = gym.spaces.Box(
      low = -np.inf,
      high = np.inf,
      shape = (obs_space,),
      dtype = np.float64,
    )


  def _connect_broker(self):
    self.context = zmq.Context.instance()
    self.broker_socket = self.context.socket(zmq.REQ)
    self.broker_socket.connect(self.env_broker_address)
    self.broker_socket.setsockopt(zmq.RCVTIMEO, 600000) # 10 Minutes

    # Get action/observation space infos
    message = RequestEnv()
    message.allocate_env = False
    message.send_info = True
    self.broker_socket.send(message.SerializeToString())
    message = AssignEnv()
    message.ParseFromString(self.broker_socket.recv())

    #print('Connected to broker at %s' % self.env_broker_address)

    # action_space = pickle.loads(message.action_space)
    # observation_space = pickle.loads(message.observation_space)

    # assert self.action_space == action_space, 'mismatch in action spaces, incompatible to remote env! - our action space has %d and theirs %d dims' % (len(self.action_space.low), len(action_space.low))
    # assert self.observation_space == observation_space, 'mismatch in observation spaces, incompatible to remote env'

  def request_new_env(self):
    # If we aren't connected to the broker yet, do so
    if self.broker_socket is None:
      self._connect_broker()
    

    unsuccessful_tries = 0
    while True:
      message = RequestEnv()
      message.allocate_env = True
      message.send_info = False
      message.hostname = self.hostname
      message.group = int(self.env_config_group)
      self.broker_socket.send(message.SerializeToString())
      message = AssignEnv()
      message.ParseFromString(self.broker_socket.recv())
      if message.address:
        break
      unsuccessful_tries += 1
      if unsuccessful_tries % 1000 == 0:
        print('Waiting for an environment for a long time: %d' % unsuccessful_tries)
      time.sleep(np.random.uniform(0.01, max(0.1, 0.5-(unsuccessful_tries/500))))

    #print("Connecting to %s" % message.address)
    return message.address
  
  def connect(self, address):
    self.socket = self.context.socket(zmq.PAIR)
    self.socket.connect(address)
  
  def parse_response(self, response, command):
    message = EnvAgent()
    message.ParseFromString(response)
    if message.command == AgentEnv.ERROR:
      try:
        orig_exception = pickle.loads(message.info)
      except:
        orig_exception = None
      raise RuntimeError('The server sent an error message', orig_exception)
    if message.command != command:
      raise RuntimeError('The server sent a package which was not ordered')
    info = None
    if message.info:
      info = pickle.loads(message.info)
    self.last_info = info
    self.last_orig_state = np.array(message.observation)
    return np.array(message.observation), message.reward, message.death, info

  def env_exchange(self, message):
    self.socket.send(message.SerializeToString(), zmq.NOBLOCK)

    if not self.socket.poll(60000, zmq.POLLIN):
      raise RuntimeError('No response from the env within 1 minute, throwing error')

    return self.parse_response(self.socket.recv(), message.command)
  
  def request_initial_state(self):
    assert self.socket
    message = AgentEnv()
    message.command = AgentEnv.REQUEST_INITIAL_STATE
    s,_,_,i = self.env_exchange(message)
    return s, i
  
  def request_step(self, action):
    assert self.socket
    message = AgentEnv()
    message.command = AgentEnv.STEP
    message.action.MergeFrom(action)
    start = time.time()
    s,r,d,i = self.env_exchange(message)
    end = time.time()
    if i is None:
      i = {}

    i["roundtrip_time"] = end-start
    return s,r,d,i
  
  def request_reset(self):
    assert self.socket
    message = AgentEnv()
    message.command = AgentEnv.RESET
    self.socket.send(message.SerializeToString())

    # No need to wait for an answer
    self.socket.close()
    self.socket = None
  
  # Request a serialized version of the environment
  def request_serialized(self):
    assert self.socket
    message = AgentEnv()
    message.command = AgentEnv.SAVE
    _, _, _, i = self.env_exchange(message)

    return i

  # Load a previously serialized state
  def request_deserialized(self, data):
    assert self.socket
    message = AgentEnv()
    message.command = AgentEnv.LOAD 
    message.saved_state = pickle.dumps(data)
    _, _, _, _ = self.env_exchange(message)

    return True

  def reset(self):
    self.action_history = []
    self.load_before_next_step = None

    # If we are connected, tell that environment that we will leave it
    if self.socket:
      try:
        self.request_reset()
      except:
        pass
    
    # Ask for a new environment at the broker and connect to it
    # Try until we could actually connect to one
    s = None
    i = None
    failed_attempts = 0
    while s is None:
      try:
        address = self.request_new_env()
        self.connect(address)
        s, i = self.request_initial_state()
      except Exception as e:
        failed_attempts += 1
        print("Could not connect, trying again")
        print(e)
        print(traceback.format_exc())
        if failed_attempts > 10:
          raise e
    
    self.balancing_log = i
    # Request the initial state after reset
    return s #, i

  def step(self, action):
    if self.load_before_next_step:
      tmp = self.load_before_next_step
      self.reset()
      self.request_deserialized(tmp)

    action = np.clip(action, self.action_space.low, self.action_space.high)
    controller_action = self.last_info['controller_action']

    try:
      s,r,d,i = self.request_step(action)
    except Exception as e:
      print(e)
      print('Connection lost, trying to re-roll')

      assert self.balancing_log is not None, 'No balancing log present'
      tmp_log = self.balancing_log
      tmp_acthist = self.action_history
      self.reset()
      self.request_deserialized(tmp_log)
      for a in tmp_acthist:
        self.request_step(a)
      self.action_history = tmp_acthist
      s,r,d,i = self.request_step(action)


    info = {
      "env_info": i,
      "orig_action": action,
      "orig_state": s,
    }

    self.action_history.append(action)

    return s,r,d,info
  
  def render(self):
    raise NotImplementedError('Rendering not supported')

  def close(self):
    if self.socket:
      self.request_reset()
    if self.broker_socket:
      self.broker_socket.close()
      self.broker_socket = None
  
  def __del__(self):
    self.close()

  def __getstate__(self):
    if self.socket:
      env_data = self.request_serialized()
    else:
      env_data = None

    return {
      "env_data": env_data,
      "action_history": self.action_history,
      "last_info": self.last_info,
      "last_orig_state": self.last_orig_state,
      "env_broker_address": self.env_broker_address,
      "env_config_group": self.env_config_group,
      "balancing_log": self.balancing_log
    }

  # Unpickle an environment
  # This skips the __init__ function, thus first we have to connect to the broker
  # In case the broker is somewhere else now, allow overwriting the address

  def __setstate__(self, d):
    self._set_spaces()   
    self._reset_client_vars()
    self.env_broker_address = d.get("env_broker_address", 'tcp://localhost:4749')
    if os.getenv("OVERWRITE_ENV_BROKER_ADDRESS"):
      self.env_broker_address = os.getenv("OVERWRITE_ENV_BROKER_ADDRESS")
    self.env_config_group = d.get('env_config_group', 0)

    if d.get("env_data", None) is not None:
      self.load_before_next_step = d.get("env_data", None)
      
    self.action_history = d.get("action_history", [])
    self.last_info = d.get("last_info", None)
    self.last_orig_state = d.get("last_orig_state", None)
    self.balancing_log = d.get("balancing_log", None)
