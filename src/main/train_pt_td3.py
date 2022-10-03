import os
import pickle
import datetime
import sys
import torch
import math
import numpy as np
from torch import nn
from torch.nn import functional as F

from garagewrapper import WindturbineGarageEnv, HParams, test_connection
from garage import wrap_experiment
from garage.envs import GymEnv, normalize
from garage.experiment.deterministic import set_seed
from garage.np.exploration_policies import AddGaussianNoise
from garage.np.policies import UniformRandomPolicy
from garage.replay_buffer import PathBuffer
from garage.sampler import FragmentWorker, LocalSampler, MultiprocessingSampler
from garage.torch import prefer_gpu
from garage.torch.algos import TD3
from garage.torch.policies import DeterministicMLPPolicy
from garage.torch.q_functions import ContinuousMLPQFunction
from garage.trainer import Trainer

assert len(sys.argv) >= 2, 'start the script with the location of a jsoned hparams file'
hparams = HParams()
print('Reading hparams from %s' % sys.argv[1])
with open(sys.argv[1], 'r') as f:
  hparams.parse_json(f.read())

assert not os.path.exists(hparams.snapshot_dir + '/itr_0.pkl'), 'use this script to start an experiment, to resume use resume_pt.py!'
assert hparams.ml_framework == 'pytorch', 'wrong framework set in hparams file'

assert test_connection(hparams), 'could not establish connection to broker'

@wrap_experiment(log_dir=hparams.snapshot_dir, use_existing_dir=True, archive_launch_repo=False, snapshot_mode='all')
def sac_windturbine(ctxt=None, seed=1, hparams=hparams):
    print('Setting up training environment')
    set_seed(seed)

    env = normalize(WindturbineGarageEnv(hparams))
    spec = env.spec

    trainer = Trainer(ctxt)

    num_timesteps = hparams.n_epochs * hparams.epoch_batch_size * hparams.get_default('steps_per_epoch', 40)

    policy = DeterministicMLPPolicy(env_spec=env.spec,
                                    hidden_sizes=hparams.get_default('policy_hidden_sizes', [256, 256]),
                                    hidden_nonlinearity=F.relu,
                                    output_nonlinearity=torch.tanh)

    exploration_policy = AddGaussianNoise(env.spec,
                                          policy,
                                          total_timesteps=hparams.get_default('noise_timesteps', hparams.n_epochs * hparams.epoch_batch_size * hparams.get_default('steps_per_epoch', 40)),
                                          max_sigma=hparams.get_default('policy_init_std', 0.1),
                                          min_sigma=hparams.get_default('policy_last_std', 1e-3))

    uniform_random_policy = UniformRandomPolicy(env.spec)

    qf1 = ContinuousMLPQFunction(env_spec=spec,
                                 hidden_sizes=hparams.get_default('value_hidden_sizes', [256, 256]),
                                 hidden_nonlinearity=F.relu)

    qf2 = ContinuousMLPQFunction(env_spec=spec,
                                 hidden_sizes=hparams.get_default('value_hidden_sizes', [256, 256]),
                                 hidden_nonlinearity=F.relu)

    replay_buffer = PathBuffer(capacity_in_transitions=int(1e6))

    sampler = MultiprocessingSampler(agents=exploration_policy,
                         envs=env,
                         max_episode_length=spec.max_episode_length,
                         n_workers=hparams.get_default('n_sample_workers', 2))

    algo = TD3(env_spec=env.spec,
              policy=policy,
              qf1=qf1,
              qf2=qf2,
              replay_buffer=replay_buffer,
              sampler=sampler,
              policy_optimizer=torch.optim.Adam,
              qf_optimizer=torch.optim.Adam,
              exploration_policy=exploration_policy,
              uniform_random_policy=uniform_random_policy,
              target_update_tau=hparams.get_default('target_update_tau', 0.005),
              discount=0.99,
              policy_noise_clip=hparams.get_default('policy_noise_clip', 0.5),
              policy_noise=hparams.get_default('policy_noise', 0.1),
              policy_lr=hparams.get_default('policy_lr', 1e-3),
              qf_lr=hparams.get_default('qf_lr', 1e-3),
              steps_per_epoch=hparams.steps_per_epoch,
              start_steps=hparams.get_default('start_steps', 1e4),
              grad_steps_per_env_step=1,
              min_buffer_size=hparams.get_default('min_buffer_size', 1e4),
              buffer_batch_size=hparams.get_default('buffer_batch_size', 100),
              max_action=1.0,
              num_evaluation_episodes=2,
              use_deterministic_evaluation=True)

    trainer.setup(algo, env)

    hparams['algorithm'] = 'td3'
    print("Using hyperparameters: ")
    print(hparams)

    with open(sys.argv[1], 'w') as f:
      f.write(hparams.to_json())

    trainer.train(n_epochs=hparams.eval_gap, batch_size=hparams.get_default('epoch_batch_size', 8000))
    try:
      sampler.shutdown_worker()
    except Exception as e:
      pass

sac_windturbine(seed=hparams.get_default('seed', 1), hparams=hparams)
