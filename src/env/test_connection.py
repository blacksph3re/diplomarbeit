import sys
import os
import zmq
import pickle
import time
import numpy as np

try:
  cur_path = os.path.dirname(os.path.abspath(__file__))
except:
  cur_path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(1, '%s/messages/python' % (os.getenv('BUILD_DIR') or os.path.abspath('%s/../../build' % cur_path)))
from agent_env_pb2 import AgentEnv, EnvAgent, WindSettings
from agent_broker_pb2 import RequestEnv, AssignEnv


def test_connection(hparams):
    context = zmq.Context.instance()
    broker_socket = context.socket(zmq.REQ)

    print('Connecting to broker')
    broker_socket.connect(hparams.get_default('env_broker_address', 'tcp://localhost:4749'))

    # Get action/observation space infos
    message = RequestEnv()
    message.allocate_env = False
    message.send_info = True
    broker_socket.send(message.SerializeToString())
    message = AssignEnv()
    message.ParseFromString(broker_socket.recv())

    action_space = pickle.loads(message.action_space)
    observation_space = pickle.loads(message.observation_space)

    print('Connection to broker successful')

    print('Connecting to environment')
    while True:
      message = RequestEnv()
      message.allocate_env = True
      message.send_info = False
      message.group = hparams.get_default('env_config_group', 0)
      broker_socket.send(message.SerializeToString())
      message = AssignEnv()
      message.ParseFromString(broker_socket.recv())
      if message.address:
        break
      time.sleep(np.random.uniform(0.01, 0.3))

    print('Got assigned an environment at %s' % message.address)

    socket = context.socket(zmq.PAIR)
    socket.connect(message.address)

    message = AgentEnv()
    message.command = AgentEnv.REQUEST_INITIAL_STATE
    socket.send(message.SerializeToString(), zmq.NOBLOCK)
    message = EnvAgent()
    message.ParseFromString(socket.recv())

    print('Received initial state, connection test successful')

    message = AgentEnv()
    message.command = AgentEnv.RESET
    socket.send(message.SerializeToString(), zmq.NOBLOCK)
    socket.close()
    broker_socket.close()

    return True