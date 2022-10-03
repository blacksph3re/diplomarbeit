#!/usr/bin/env python3
"""This is an example to train a task with PPO algorithm (PyTorch).
Here it runs InvertedDoublePendulum-v2 environment with 100 iterations.
"""
import torch

from garage import wrap_experiment
from garage.envs import normalize
from garage.experiment.deterministic import set_seed
from garage.trainer import Trainer
from garagewrapper import WindturbineGarageEnv, HParams
import sys
import os
import pickle
import datetime

assert len(sys.argv) >= 2, 'start the script with the location of a jsoned hparams file'
hparams = HParams()
print('Reading hparams from %s' % sys.argv[1])
with open(sys.argv[1], 'r') as f:
  hparams.parse_json(f.read())
print(hparams)

assert len([x for x in os.listdir(hparams.snapshot_dir) if x.startswith('itr_')]), 'use this script to resume an already started experiment!'
assert hparams.ml_framework == 'pytorch', 'wrong framework set in hparams file'

@wrap_experiment(log_dir=hparams.snapshot_dir, use_existing_dir=True, archive_launch_repo=False, snapshot_mode='gap', snapshot_gap=hparams.get_default('snapshot_gap', 2))
def ppo_windturbine(ctxt, seed, hparams):
  set_seed(seed)

  start_epoch = max([int(x[4:-4]) for x in os.listdir(hparams.snapshot_dir) if x.startswith('itr_')])

  trainer = Trainer(ctxt)

  print("Loading from %s epoch %d" % (hparams.snapshot_dir, start_epoch))
  cfg = trainer.restore(hparams.snapshot_dir, start_epoch)

  if cfg.n_epochs >= hparams.n_epochs:
    print('Training finished, exiting with code 42')
    exit(42)

  trainer.resume(n_epochs=hparams.eval_gap+cfg.n_epochs)
  trainer.save(hparams.eval_gap+cfg.n_epochs)

  # print('Cleaning up unnecessary iterations')
  # assert os.path.exists('%s/itr_%d.pkl' % (hparams.snapshot_dir, cfg.start_epoch+hparams.eval_gap))
  # for i in range(cfg.start_epoch, cfg.start_epoch + hparams.eval_gap - 1):
  #   os.remove('%s/itr_%d.pkl' % (hparams.snapshot_dir, i))
  #   os.symlink('%s/itr_%d.pkl' % (hparams.snapshot_dir, i),
  #              '%s/itr_%d.pkl' % (hparams.snapshot_dir, cfg.start_epoch + hparams.eval_gap))

  print('Stopping and resuming experiment')

  try:
    trainer._shutdown_worker()
  except:
    pass


ppo_windturbine(seed=hparams.get_default('seed', 1), hparams=hparams)