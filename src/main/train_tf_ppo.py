import os
import pickle
import tensorflow as tf
import datetime
import sys

from garagewrapper import WindturbineGarageEnv, HParams
from garage import wrap_experiment
from garage.envs import normalize
from garage.experiment.deterministic import set_seed
from garage.sampler import RaySampler
from garage.tf.algos import PPO
from garage.tf.baselines import GaussianMLPBaseline
from garage.tf.policies import GaussianMLPPolicy
from garage.trainer import TFTrainer

x = None

assert len(sys.argv) >= 2, 'start the script with the location of a jsoned hparams file'
hparams = HParams()
print('Reading hparams from %s' % sys.argv[1])
with open(sys.argv[1], 'r') as f:
  hparams.parse_json(f.read())


@wrap_experiment(log_dir=hparams.snapshot_dir, use_existing_dir=True, snapshot_mode='all')
def ppo_windturbine(ctxt=None, seed=1, hparams=HParams()):
    """Train PPO with InvertedDoublePendulum-v2 environment.
    Args:
        ctxt (garage.experiment.ExperimentContext): The experiment
            configuration used by Trainer to create the snapshotter.
        seed (int): Used to seed the random number generator to produce
            determinism.
    """
    set_seed(seed)
    with TFTrainer(snapshot_config=ctxt) as trainer:
        
        env = normalize(WindturbineGarageEnv(hparams))
        print("Using hyperparameters: ")
        print(hparams)

        with open(sys.argv[1], 'w') as f:
          f.write(hparams.to_json())

        if os.path.exists(hparams.snapshot_dir + '/itr_0.pkl'):
          start_epoch = 0
          while os.path.exists(hparams.snapshot_dir + '/itr_%d.pkl' % (start_epoch + 1)):
            start_epoch += 1

          print("Loading from %s epoch %d" % (hparams.snapshot_dir, start_epoch))
          cfg = trainer.restore(hparams.snapshot_dir, start_epoch)

          print('Running an eval run at %d' % cfg.start_epoch)
          trainer._start_worker()
          data = {
            "episodes": trainer.obtain_episodes(cfg.start_epoch),
            "hparams": hparams.get_dict(),
            "config": cfg.__dict__,
            "time": datetime.datetime.now(),
          }
          with open('%s/eval_%d.pkl' % (hparams.snapshot_dir, cfg.start_epoch), 'wb') as f:
            pickle.dump(data, f)
          

          if cfg.n_epochs >= hparams.n_epochs:
            print('Training finished, exiting with code 42')
            exit(42)
          trainer.resume(n_epochs=hparams.eval_gap+cfg.n_epochs)
          trainer.save(hparams.eval_gap+cfg.n_epochs)
          trainer._shutdown_worker()

        else:
          print("Starting a fresh run")
          policy = GaussianMLPPolicy(
              env_spec=env.spec,
              hidden_sizes=(64, 64),
              hidden_nonlinearity=tf.nn.tanh,
              output_nonlinearity=tf.nn.tanh,
              init_std=hparams.policy_init_std,
              learn_std=True,
              adaptive_std=False,
          )

          baseline = GaussianMLPBaseline(
              env_spec=env.spec,
              hidden_sizes=(64, 32),
              hidden_nonlinearity=tf.nn.tanh,
              use_trust_region=True,
              adaptive_std=False,
          )

          sampler = RaySampler(agents=policy,
                              envs=env,
                              max_episode_length=env.spec.max_episode_length,
                              is_tf_worker=True,
                              n_workers=2)

          # NOTE: make sure when setting entropy_method to 'max', set
          # center_adv to False and turn off policy gradient. See
          # tf.algos.NPO for detailed documentation.
          algo = PPO(
              env_spec=env.spec,
              policy=policy,
              baseline=baseline,
              sampler=sampler,
              discount=0.99,
              gae_lambda=0.95,
              lr_clip_range=0.2,
              optimizer_args=dict(
                  batch_size=32,
                  max_optimization_epochs=10,
              ),
              stop_entropy_gradient=False,
              entropy_method='regularized',
              policy_ent_coeff=0.01,
              center_adv=True,
              use_neg_logli_entropy=True,
          )

          trainer.setup(algo, env)
          trainer.train(n_epochs=hparams.eval_gap, batch_size=5000, plot=False, store_episodes=False)
        
        env.close()


ppo_windturbine(seed=1, hparams=hparams)
