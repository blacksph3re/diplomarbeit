import subprocess
import os
import sys
import pandas as pd
from helpers import get_broker_address, start_training, resume_training

sys.path.insert(1, '../env')
from hparams import HParams

broker_address = get_broker_address()

hparams = HParams(
  eval_gap = 10,
  n_epochs = 300,
  n_sample_workers = int(os.getenv('N_SAMPLE_WORKERS') or 2),
  env_broker_address = broker_address,
  max_trajectory_length = 2000,
  epoch_batch_size = 32000,
  snapshot_dir = os.getenv('RESULT_DIR') or 'data/sac_windturbine_1',
  code_dir = os.getenv('PYTHON') + '/main' if os.getenv('PYTHON') else os.getcwd(),
  differential_control_play = 0.05,
  policy_init_std = 0.3,
  policy_hidden_sizes = [256, 256],
  value_hidden_sizes = [256, 256],
  ml_framework = 'pytorch',
  mask_act = 'individual-pitch-no-torque',
  seed = 2,
)

print('Starting run_local.py')

progress, _ = start_training(hparams, {'env_broker_address': broker_address})

assert 'Evaluation/Iteration' in progress
#assert progress['Evaluation/Iteration'].max() > 0

last_iter = progress['Evaluation/Iteration'].max()

handles = []

# Then resume until done
while last_iter < hparams.n_epochs:
  progress, _ = resume_training(hparams, progress)
  
  last_iter = progress['Evaluation/Iteration'].max()


print('Waiting for %d evaluation scripts to finish' % len(handles))
for h in handles:
  h.wait()