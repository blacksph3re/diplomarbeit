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
from garage.envs import normalize
from garage.experiment.deterministic import set_seed
from garage.replay_buffer import PathBuffer
from garage.sampler import FragmentWorker, LocalSampler, MultiprocessingSampler, RaySampler
from garage.torch import set_gpu_mode
from garage.torch.algos import SAC
from garage.torch.policies import TanhGaussianMLPPolicy
from garage.torch.q_functions import ContinuousMLPQFunction
from garage.trainer import Trainer


assert len(sys.argv) >= 2, 'start the script with the location of a jsoned hparams file'
hparams = HParams()
print('Reading hparams from %s' % sys.argv[1])
with open(sys.argv[1], 'r') as f:
  hparams.parse_json(f.read())

assert not os.path.exists(hparams.snapshot_dir + '/itr_0.pkl'), 'use this script to start an experiment, to resume use resume_pt.py!'
assert hparams.ml_framework == 'pytorch', 'wrong framework set in hparams file'

# assert test_connection(hparams), 'could not establish connection to broker'

@wrap_experiment(log_dir=hparams.snapshot_dir, use_existing_dir=True, archive_launch_repo=False, snapshot_mode='gap', snapshot_gap=hparams.get_default('snapshot_gap', 2))
def sac_windturbine(ctxt=None, seed=1, hparams=hparams):
    print('Setting up training environment')
    set_seed(seed)

    env = normalize(WindturbineGarageEnv(hparams))
    spec = env.spec
    print(spec)

    trainer = Trainer(ctxt)

    nonlinearities = {
      'relu': nn.ReLU,
      'tanh': nn.Tanh
    }

    if hparams.get_default('restore_policy_from', None) is None:
      policy = TanhGaussianMLPPolicy(
          env_spec=spec,
          hidden_sizes=hparams.get_default('policy_hidden_sizes', [256, 256]),
          hidden_nonlinearity=nonlinearities[hparams.get_default('hidden_nonlinearity', 'relu')],
          output_nonlinearity=None,
          min_std=np.exp(-20.),
          max_std=np.exp(0.),
          init_std=hparams.get_default('policy_init_std', 0.3)
      )
    else:
      with open(hparams['restore_policy_from'], 'rb') as f:
        checkpoint = pickle.load(f)
      policy = checkpoint['algo'].policy

    # Reduce the weights for the last policy layer that predicts the mean
    if hparams.get_default('tiny_policy_output_weights', False):
      policy._module._shared_mean_log_std_network._output_layers[0].linear.weight = nn.Parameter(policy._module._shared_mean_log_std_network._output_layers[0].linear.weight / 100)

    if hparams.get_default('restore_qf_from', None) is None:
      qf1 = ContinuousMLPQFunction(env_spec=spec,
                                  hidden_sizes=hparams.get_default('value_hidden_sizes', [256, 256]),
                                  hidden_nonlinearity=nonlinearities[hparams.get_default('hidden_nonlinearity', 'relu')])

      qf2 = ContinuousMLPQFunction(env_spec=spec,
                                  hidden_sizes=hparams.get_default('value_hidden_sizes', [256, 256]),
                                  hidden_nonlinearity=nonlinearities[hparams.get_default('hidden_nonlinearity', 'relu')])
    else:
      with open(hparams['restore_qf_from'], 'rb') as f:
        checkpoint = pickle.load(f)
      qf1 = checkpoint['algo']._qf1
      qf2 = checkpoint['algo']._qf2

    replay_buffer = PathBuffer(capacity_in_transitions=int(hparams.get_default('replay_buffer_size', 1e6)))

    sampler = MultiprocessingSampler(agents=policy,
                         envs=env,
                         max_episode_length=spec.max_episode_length,
                         n_workers=hparams.get_default('n_sample_workers', 2))

    algo = SAC(env_spec=spec,
              policy=policy,
              qf1=qf1,
              qf2=qf2,
              sampler=sampler,
              gradient_steps_per_itr=hparams.get_default('gradient_steps_per_itr', 100),
              max_episode_length_eval=spec.max_episode_length,
              replay_buffer=replay_buffer,
              min_buffer_size=hparams.get_default('min_buffer_size', 2e5),
              target_update_tau=hparams.get_default('target_update_tau', 5e-3),
              discount=hparams.get_default('discount', 0.99),
              buffer_batch_size=hparams.get_default('buffer_batch_size', 256),
              reward_scale=1.,
              steps_per_epoch=hparams.get_default('steps_per_epoch', 1),
              policy_lr=hparams.get_default('policy_lr', 1e-4),
              qf_lr=hparams.get_default('qf_lr', 3e-4),
              num_evaluation_episodes=hparams.get_default('num_sac_evaluation_episodes',1),
              initial_log_entropy=math.log(hparams.get_default('policy_init_std', 0.3)),
              target_entropy=hparams.get_default('target_entropy', None),
              temporal_regularization_factor=hparams.get_default('caps_lambda_t', 0.),
              spatial_regularization_factor=hparams.get_default('caps_lambda_s', 0.),
              spatial_regularization_eps=hparams.get_default('caps_eps_s', 1.),
              dr3_regularization_factor=hparams.get_default('dr3_regularization', 0.),
              temporal_q_regularization_factor=hparams.get_default('temporal_q_regularization', 0.))

    trainer.setup(algo, env)

    hparams['algorithm'] = 'sac'
    print("Using hyperparameters: ")
    print(hparams)

    with open(sys.argv[1], 'w') as f:
      f.write(hparams.to_json())

    trainer.train(n_epochs=hparams.eval_gap+1, batch_size=hparams.get_default('epoch_batch_size', 8000))
    try:
      sampler.shutdown_worker()
    except Exception as e:
      pass

sac_windturbine(seed=hparams.get_default('seed', 1), hparams=hparams)
