import os
import subprocess
import pandas as pd
from pathlib import Path
import json
import time


def get_broker_address():
  broker_address='tcp://localhost:4749'
  if os.getenv('LOAD_BROKER_HOST_FROM_FILE'):
    while True:
      try:
        with open(os.getenv('LOAD_BROKER_HOST_FROM_FILE'), 'r') as f:
          broker_hostname = f.read().strip()
        assert len(broker_hostname) > 0
        break
      except:
        print('Could not load broker host from file, retrying')
        time.sleep(1)
    broker_address='tcp://%s:%s' % (broker_hostname, 4749)

  return broker_address

def recover_progress(snapshot_dir):
  try:
    total_progress = pd.read_csv('%s/total_progress.csv' % snapshot_dir)
    assert len(total_progress)
  except:
    total_progress = None
  try:
    progress = pd.read_csv('%s/progress.csv' % snapshot_dir)
    assert len(progress)
  except:
    progress = None

  if total_progress is None and progress is None:
    raise RuntimeError('Could not read either total_progress.csv or progress.csv')
  elif total_progress is None:
    print('Warning, could not read total_progress.csv - training likely ended early')
    #progress.to_csv('%s/total_progress.csv' % snapshot_dir, index=False)
    #os.remove('%s/progress.csv' % snapshot_dir)
  elif progress is None:
    progress = total_progress
  elif progress['Evaluation/Iteration'].max() > total_progress['Evaluation/Iteration'].max():
    print('Warning, some iterations were not copied over to total_progress.csv - training likely ended early')
    progress = total_progress.append(progress)
    #progress.to_csv('%s/total_progress.csv' % snapshot_dir, index=False)
    #os.remove('%s/progress.csv' % snapshot_dir)

  return progress
  

def check_resume(hparams, rewrite_hparams):
  Path(hparams['snapshot_dir']).mkdir(parents=True, exist_ok=True)

  if 'code_dir' not in hparams and 'code_dir' not in rewrite_hparams:
    rewrite_hparams['code_dir'] = '.'

  resume = False
  if not os.path.exists('%s/hparams.json' % hparams['snapshot_dir']):
    try:
      json_repr = hparams.to_json()
    except:
      json_repr = json.dumps(hparams)
    
    with open('%s/hparams.json' % hparams['snapshot_dir'], 'w') as f:
      f.write(json_repr)
  else:
    print('Using previous hparams')
    with open('%s/hparams.json' % hparams['snapshot_dir'], 'r') as f:
      json_repr = f.read()
    try:
      hparams.parse_json(json_repr)
    except:
      hparams = json.loads(json_repr)
    
    rewritten = False
    for k, v in rewrite_hparams.items():
      if k not in hparams or hparams[k] != v:
        print('Rewriting hparam[%s] to %s' % (k, v))
        hparams[k] = v
        rewritten = True
    if rewritten:
      try:
        json_repr = hparams.to_json()
      except:
        json_repr = json.dumps(hparams)
      
      with open('%s/hparams.json' % hparams['snapshot_dir'], 'w') as f:
        f.write(json_repr)


    resume = True
  return resume

# Start training or resume from checkpoint
def start_training(hparams, rewrite_hparams):
  resume = check_resume(hparams, rewrite_hparams)

  print('Hparams:')
  print(str(hparams))

  if not resume:
    print('Starting fresh training')
    with open('%s/train-%s.log' % (hparams['log_dir'], hparams['tune_trial_id']), 'w') as f:
      retcode = subprocess.call(['python', '%s/train.py' % hparams['code_dir'], '%s/hparams.json' % hparams['snapshot_dir']], stdout=f, stderr=subprocess.STDOUT, env=os.environ)
    if retcode != 0:
      print('Warning - Train.py returned with a non-zero retcode %d' % retcode)

    progress = pd.read_csv('%s/progress.csv' % hparams['snapshot_dir'])
    progress.to_csv('%s/total_progress.csv' % hparams['snapshot_dir'], index=False)
    os.remove('%s/progress.csv' % hparams['snapshot_dir'])

    return progress, progress
  else:
    progress = recover_progress(hparams['snapshot_dir'])
    progress.to_csv('%s/total_progress.csv' % hparams['snapshot_dir'], index=False)

    return progress, pd.DataFrame()
  


def resume_training(hparams, progress):
  last_iter = progress['Evaluation/Iteration'].max()
  handles = []

  # print('Launching an evaluation run at %d' % last_iter)
  # handles.append(subprocess.Popen(['python', '%s/evaluate.py' % hparams['code_dir'], hparams['snapshot_dir'], str(last_iter)]))

  # for i in range(last_iter-1):
  #   if 'extra_evals_every' in hparams and i % hparams['extra_evals_every'] == 0 and \
  #     os.path.exists('%s/itr_%d.pkl' % (hparams['snapshot_dir'], i)) and \
  #     not os.path.exists('%s/eval_%d.pkl' % (hparams['snapshot_dir'], i)):
  #     print('Launching an evaluation run at %d' % i)
  #     handles.append(subprocess.Popen(['python', '%s/evaluate.py' % hparams['code_dir'], hparams['snapshot_dir'], str(i)]))


  try:
    tries = 0
    while last_iter == progress['Evaluation/Iteration'].max():
      if tries == 0:
        print('Resuming training operation')
      elif tries < 3:
        print('Resuming failed, trying again')
      else:
        print('Resume seems to hang, crashing')
        raise RuntimeError('Could not resume training')

      resume_file = '%s/resume_pt.py' % hparams['code_dir'] if hparams['ml_framework'] == 'pytorch' else '%s/resume_tf.py' % hparams['code_dir']
      with open('%s/resume_%s_%d_%d.log' % (hparams['log_dir'], hparams['tune_trial_id'], last_iter, tries), 'w') as f:
        retcode = subprocess.call(['python', resume_file, '%s/hparams.json' % hparams['snapshot_dir']], stdout=f, stderr=subprocess.STDOUT, env=os.environ)
      if retcode != 0:
        print('Warning - %s returned with a non-zero retcode %d' % (resume_file, retcode))

      try:
        cur_progress = pd.read_csv('%s/progress.csv' % hparams['snapshot_dir'])
        progress = progress.append(cur_progress)
        progress.to_csv('%s/total_progress.csv' % hparams['snapshot_dir'], index=False)
        os.remove('%s/progress.csv' % hparams['snapshot_dir'])
      except Exception as e:
        print(e)
  finally:
    for handle in handles:
      handle.wait()
  
  return progress, cur_progress