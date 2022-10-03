# An env encapsulation client
# Can be run as a separate file on either the same machine or remotely

import argparse
import zmq
import pickle
import numpy as np
import time
import psutil
import os
import sys
import tempfile
import socket
import signal
import traceback
import shutil
import base64
import toml
from qbladeadapter import QBladeAdapter


config_file = os.getenv('BASE_CONFIG_FILE') or sys.argv[1]
print('Loading from base config file %s:' % config_file)

with open(config_file, 'r') as f:
  config = toml.load(f)

if os.getenv("OVERWRITE_CONFIG_FILE") or len(sys.argv) > 2:
  config_overwrite_file = os.getenv("OVERWRITE_CONFIG_FILE") or sys.argv[2]
  print('Loading overwrite config from %s' % config_overwrite_file)
  with open(config_overwrite_file, 'r') as f:
    config_overwrite = toml.load(f)
  
  def merge(a, b):
    for key in b:
      if not key in a:
        a[key] = b[key]
      elif isinstance(b[key], dict):
        merge(a[key], b[key])
      else:
        a[key] = b[key]
  
  merge(config, config_overwrite)
  

config['net']['bind_port'] = config['net'].get('bind_port', '*')
config['net']['hostname'] = config['net'].get('hostname', socket.gethostname())
config['net']['bind_address'] = config['net'].get('bind_address', '*')
config['broker']['port'] = config['broker'].get('port', '4748')
config['broker']['hostname'] = config['broker'].get('hostname', 'localhost')

if os.getenv('LOAD_BROKER_HOST_FROM_FILE'):
  while True:
    try:
      with open(os.getenv('LOAD_BROKER_HOST_FROM_FILE'), 'r') as f:
        config['broker']['hostname'] = f.read().strip()
      assert len(config['broker']['hostname']) > 0
      break
    except:
      print('Could not load broker host from file, retrying')
      time.sleep(1)


config['binaries']['qblade_library'] = os.path.abspath(config['binaries']['qblade_library'])
config['binaries']['controller_library'] = os.path.abspath(config['binaries']['controller_library'])
config['binaries']['turbsim_binary'] = os.path.abspath(config['binaries']['turbsim_binary'])
config['binaries']['preload_chrono'] = os.path.abspath(config['binaries']['preload_chrono']) if 'preload_chrono' in config['binaries'] else ''
config['binaries']['pb_message_folder'] = os.path.abspath(config['binaries']['pb_message_folder'])


sys.path.insert(1, config['binaries']['pb_message_folder'])
import env_broker_pb2 as env_broker
import agent_env_pb2 as agent_env

config['server']['working_dir'] = os.path.abspath(config['server'].get('working_dir', tempfile.mkdtemp(prefix='qblade_', suffix=str(base64.b32encode(np.random.bytes(10)), 'utf-8'))))
config['server']['time_limit'] = config['server'].get('time_limit', 999999)
config['server']['cycles'] = config['server'].get('cycles')

config['qblade']['project'] = os.path.abspath(config['qblade']['project'])
assert 'yaw_control' in config['qblade']
assert 'gearbox_ratio' in config['qblade']
assert 'max_generator_torque' in config['qblade']
assert 'max_blade_pitch' in config['qblade']
assert 'max_yaw' in config['qblade']
assert 'turbulent_wind' in config['qblade']
assert 'windspeed_type' in config['qblade']
assert 'windspeed_value' in config['qblade']
assert 'inflow_angle_hor_type' in config['qblade']
assert 'inflow_angle_hor_value' in config['qblade']
assert 'inflow_angle_vert_type' in config['qblade']
assert 'inflow_angle_vert_value' in config['qblade']
assert 'rng_seed_type' in config['qblade']
assert 'rng_seed_value' in config['qblade']
assert 'init_rotor_azimuth_type' in config['qblade']
assert 'init_rotor_azimuth_value' in config['qblade']
assert 'group' in config['qblade']

print(config)

os.chdir(config['server']['working_dir'])
print('Preparing working dir %s' % config['server']['working_dir'])
try:
  os.mkdir('./ControllerFiles')
  os.mkdir('./Binaries')
  shutil.copyfile(config['binaries']['controller_library'], './ControllerFiles/TUBCon_1.3.9_64Bit.so')
  shutil.copyfile(config['binaries']['turbsim_binary'], './Binaries/TurbSim64')
  shutil.copytree(config['qblade']['project'], './Project')
  config['qblade']['qblade_definition'] = '%s/Project/project.def' % config['server']['working_dir']
except Exception as e:
  print('Could not prepare working directory')
  print(e)
  print(config)
  exit(1)

env = QBladeAdapter(config)
#env.reset()

cpu_count = int(os.getenv('OMP_NUM_THREADS') or psutil.cpu_count())

global_vars = {}
global_vars['server_address'] = 'tcp://%s:%s' % (config['net']['hostname'], config['net']['bind_port'])
global_vars['steps_since_last_send'] = 0
global_vars['global_id'] = 0
global_vars['cycles_since_boot'] = 0
global_vars['steps_since_reset'] = 0
global_vars['first_work_time'] = time.time()
global_vars['last_send_time'] = time.time()
global_vars['start_time'] = time.time()
global_vars['idle_time_since_last_send'] = 0

context = zmq.Context()

broker_address='tcp://%s:%s' % (config['broker']['hostname'], config['broker']['port'])
print('Starting env server in %s, connecting to broker at %s' % (os.getcwd(), broker_address))
broker_socket = context.socket(zmq.REQ)
broker_socket.connect(broker_address)
socket = None

def register():
  message = env_broker.StatusUpdate()
  message.address = global_vars['server_address']
  message.qblade_library = config['binaries']['qblade_library']
  message.project_file = config['qblade']['project']
  message.group = config['qblade']['group']
  message.id = 0
  message.status = env_broker.StatusUpdate.INITIALIZING
  message.cpu_count = cpu_count
  message.action_space = pickle.dumps(env.action_space)
  message.observation_space = pickle.dumps(env.observation_space)

  print('Registering as %s with %d dims action and %d dims obs' % (global_vars['server_address'], env.action_space.shape[0], env.observation_space.shape[0]))
  broker_socket.send(message.SerializeToString())

  message = env_broker.StatusUpdateConfirmation()
  message.ParseFromString(broker_socket.recv())
  assert not message.reconnect

  print('Received id %d' % message.id)
  return message.id

def receive_confirmation():
  message = env_broker.StatusUpdateConfirmation()
  message.ParseFromString(broker_socket.recv())

  if message.reconnect:
    print('Server tells us to reconnect, restarting process')
    cleanup()
    exit()
  
def send_to_broker(status, noblock=False):
  message = env_broker.StatusUpdate()
  message.status = status
  message.id = global_vars['global_id']
  time_passed = (time.time() - global_vars['last_send_time'])
  message.load = (time_passed - global_vars['idle_time_since_last_send']) / time_passed
  message.address = global_vars['server_address']
  message.cpu_count = cpu_count
  message.steps_computed = global_vars['steps_since_last_send']
  message.group = config['qblade']['group']
  global_vars['steps_since_last_send'] = 0
  global_vars['idle_time_since_last_send'] = 0
  global_vars['last_send_time'] = time.time()
  if noblock:
    broker_socket.send(message.SerializeToString(), zmq.NOBLOCK)
    # Don't wait for a confirmation, just shut down
  else:
    broker_socket.send(message.SerializeToString())
    receive_confirmation()

def notify_resetting():
  send_to_broker(env_broker.StatusUpdate.RESETTING)

def notify_idle():
  send_to_broker(env_broker.StatusUpdate.IDLE)

def notify_working():
  send_to_broker(env_broker.StatusUpdate.WORKING)

def notify_shutdown():
  send_to_broker(env_broker.StatusUpdate.SHUTTING_DOWN, True)

def send_to_agent(socket, command, observation=[], reward=0, death=False, info={}, noblock=False):
  message = agent_env.EnvAgent()
  message.command = command
  message.reward = reward
  message.death = death
  message.observation.MergeFrom(observation)
  message.info = pickle.dumps(info)
  if noblock:
    socket.send(message.SerializeToString(), zmq.NOBLOCK)
  else:
    socket.send(message.SerializeToString())

def cleanup():
  try:
    if broker_socket and not broker_socket.closed:
      notify_shutdown()
      broker_socket.close()
    
    shutil.rmtree(config['server']['working_dir'])

    if socket and not socket.closed:
      send_to_agent(socket, agent_env.AgentEnv.ERROR, noblock=True)

  except Exception as e:
    print('Could not clean up!')
    print(e)
    traceback.print_tb(e.__traceback__)

def sig_handler(signum, frame):
  print('Received interrupt %s, shutting down %s' % (signum, frame))
  cleanup()
  exit(-1)

signal.signal(signal.SIGSEGV, sig_handler)
signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

global_vars['global_id'] = register()

try:
  while global_vars['cycles_since_boot'] < config['server']['cycles'] and time.time() - global_vars['start_time'] < config['server']['time_limit']: # After 500 resets, restart
    print('Resetting, cycles left %d, time left %d sec' % (config['server']['cycles'] - global_vars['cycles_since_boot'], config['server']['time_limit'] - time.time() + global_vars['start_time']))
    notify_resetting()
    observation, info = env.reset()

    socket = context.socket(zmq.PAIR)
    socket.bind('tcp://%s:%s' % (config['net']['bind_address'], config['net']['bind_port']))
    
    if config['net']['bind_port'] == "*" or config['net']['bind_port'] == "0":
      bound = socket.getsockopt(zmq.LAST_ENDPOINT)
      tmp_port = int(bound.split(b':')[-1])
      global_vars['server_address'] = "tcp://%s:%d" % (config['net']['hostname'], tmp_port)

    print('Reset done, awaiting connections from new client at %s' % global_vars['server_address'])


    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    notify_idle()

    has_notified_working = False
    last_notification = time.time()
    last_work = time.time()

    global_vars['steps_since_reset'] = 0

    while True:
      poll_start = time.time()
      pulled = dict(poller.poll(1000))
      global_vars['idle_time_since_last_send'] += time.time() - poll_start
    

      if socket in pulled and pulled[socket] == zmq.POLLIN:
        message = agent_env.AgentEnv()
        message.ParseFromString(socket.recv())
        last_work = time.time()

        if message.command == agent_env.AgentEnv.REQUEST_INITIAL_STATE:
          send_to_agent(socket, message.command, observation, 0, False, info)
          #global_vars['steps_since_reset'] += 1000
          global_vars['steps_since_last_send'] += 1000
        
        elif message.command == agent_env.AgentEnv.STEP:
          try:
            a = np.array(message.action)
            s,r,d,i = env.step(a)
            if i == None:
              i = {}
            
            i['hostname'] = config['net']['hostname']
            i['cpu_count'] = cpu_count
            i['group'] = config['qblade']['group']

            # if global_vars['steps_since_reset'] > 400:
            #   print('crashing')
            #   exit(-1)
            
            send_to_agent(socket, message.command, s, r, d, i)
            global_vars['steps_since_last_send'] += 1
            global_vars['steps_since_reset'] += 1
          except Exception as e:
            print('Could not step environment: ', e)
            send_to_agent(socket, agent_env.AgentEnv.ERROR, [], 0, False, e)
            break

        elif message.command == agent_env.AgentEnv.SAVE:
          send_to_agent(socket, message.command, [], 0, False, {'log': env.log})
          print('Sent execution log to agent')

        elif message.command == agent_env.AgentEnv.LOAD:
          try:
            log = pickle.loads(message.saved_state)['log']
            print('Unrolling log from saved state, %d steps to simulate' % len(log))

            env.rollout_log(log)
          
            send_to_agent(socket, message.command, [], 0, False, [])
            print('Successfully unrolled log')
          except Exception as e:
            send_to_agent(socket, agent_env.AgentEnv.ERROR, [], 0, False, e)
            print('Could not unroll log, resetting')
            print(e)
            print(traceback.format_exc())
            break

        elif message.command == agent_env.AgentEnv.RESET:
          global_vars['cycles_since_boot'] += 1
          print('Steps since reset: %d (%f it/s)' % (global_vars['steps_since_reset'], global_vars['steps_since_reset'] / (time.time() - global_vars['first_work_time'])))
          break
        
        if not has_notified_working:
          print('Received first work packet')
          global_vars['first_work_time'] = last_work
          notify_working()
          last_notification = time.time()
          has_notified_working = True

      # Regularly send heartbeats to the server
      # We choose an interval of 5 seconds
      if time.time() - last_notification > 5:
        if has_notified_working:
          notify_working()
        else:
          notify_idle()
        last_notification = time.time()
      
      # If we spent too much time (>1 min) without a command for the client, we assume its dead
      # A high timeout is needed because if this happens in normal operation, the agent sees weird data
      # and we might mess up training
      if has_notified_working and (time.time() - last_work > 60):
        print('Disconnecting from client due to long inactivity')
        try:
          send_to_agent(socket, agent_env.AgentEnv.ERROR, noblock=True)
        except:
          print('Could not close client connection to inactive client, it likely died')
        break

      # If we spent a lot of time (>1h) without ever receiving work, shut down too
      if time.time() - last_work > 3600:
        print('Did not receive anything to do for >1h, shutting down')
        cleanup()
        exit(1)

    socket.close()
except Exception as e:
  print('Uncaught exception: ', e)

print('Shutting down server')
cleanup()