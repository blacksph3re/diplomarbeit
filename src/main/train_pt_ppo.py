#!/usr/bin/env python3
"""This is an example to train a task with PPO algorithm (PyTorch).
Here it runs InvertedDoublePendulum-v2 environment with 100 iterations.
"""
import torch
import numpy as np
from garage import wrap_experiment
from garage.envs import normalize
from garage.experiment.deterministic import set_seed
from garage.sampler import RaySampler, MultiprocessingSampler
from garage.torch.algos import PPO
from garage.torch.policies import GaussianMLPPolicy
from garage.torch.value_functions import GaussianMLPValueFunction
from garage.torch.optimizers import OptimizerWrapper
from garage.trainer import Trainer
from garagewrapper import WindturbineGarageEnv, HParams, test_connection
import sys
import os


assert len(sys.argv) >= 2, 'start the script with the location of a jsoned hparams file'
hparams = HParams()
print('Reading hparams from %s' % sys.argv[1])
with open(sys.argv[1], 'r') as f:
  hparams.parse_json(f.read())

assert not os.path.exists(hparams.snapshot_dir + '/itr_0.pkl'), 'use this script to start an experiment, to resume use resume_pt.py!'
assert hparams.ml_framework == 'pytorch', 'wrong framework set in hparams file'

assert test_connection(hparams), 'could not establish connection to broker'

@wrap_experiment(log_dir=hparams.snapshot_dir, use_existing_dir=True, archive_launch_repo=False, snapshot_mode='all')
def ppo_windturbine(ctxt=None, seed=1, hparams=hparams):
    """Train PPO with InvertedDoublePendulum-v2 environment.
    Args:
        ctxt (garage.experiment.ExperimentContext): The experiment
            configuration used by Trainer to create the snapshotter.
        seed (int): Used to seed the random number generator to produce
            determinism.
    """
    set_seed(seed)

    env = normalize(WindturbineGarageEnv(hparams))
    spec = env.spec

    trainer = Trainer(ctxt)

    
    policy = GaussianMLPPolicy(spec,
                               hidden_sizes=hparams.policy_hidden_sizes,
                               hidden_nonlinearity=torch.relu,
                               output_nonlinearity=torch.tanh,
                               init_std=hparams.policy_init_std,
                               min_std=np.exp(-20.),
                               max_std=np.exp(0.),
                               learn_std=True
                               )

    value_function = GaussianMLPValueFunction(env_spec=spec,
                                              hidden_sizes=hparams.value_hidden_sizes,
                                              hidden_nonlinearity=torch.relu,
                                              output_nonlinearity=None)

    sampler = MultiprocessingSampler(agents=policy,
                         envs=env,
                         max_episode_length=spec.max_episode_length,
                         n_workers=hparams.get_default('n_sample_workers', 2))

    algo = PPO(env_spec=spec,
               policy=policy,
               policy_optimizer=OptimizerWrapper(
                (torch.optim.Adam, dict(lr=hparams.get_default('policy_lr', 2.5e-4))),
                policy,
                max_optimization_epochs=hparams.get_default('policy_optimsteps', 10),
                minibatch_size=hparams.get_default('policy_batchsize', 256)),
               value_function=value_function,
               vf_optimizer=OptimizerWrapper(
                (torch.optim.Adam, dict(lr=hparams.get_default('value_lr', 2.5e-4))),
                value_function,
                max_optimization_epochs=hparams.get_default('value_optimsteps', 10),
                minibatch_size=hparams.get_default('value_batchsize', 256)),
               sampler=sampler,
               num_train_per_epoch=hparams.get_default('num_train_per_epoch', 1),
               discount=hparams.get_default('discount', 0.99),
               gae_lambda=hparams.get_default('gae_lambda', 0.95),
               lr_clip_range=hparams.get_default('lr_clip_range', 0.2),
               center_adv=hparams.get_default('center_adv', True),
               entropy_method=hparams.get_default('entropy_method', 'regularized'),
               policy_ent_coeff=hparams.get_default('policy_ent_coeff', 0.001),
               stop_entropy_gradient=hparams.get_default('stop_entropy_gradient', False))

    hparams['algorithm'] = 'ppo'
    print("Using hyperparameters: ")
    print(hparams)

    with open(sys.argv[1], 'w') as f:
      f.write(hparams.to_json())

    trainer.setup(algo, env)
    trainer.train(n_epochs=hparams.eval_gap, batch_size=hparams.get_default('epoch_batch_size', 8000))
    try:
      sampler.shutdown_worker()
    except Exception as e:
      pass

ppo_windturbine(seed=hparams.get_default('seed', 1), hparams=hparams)
