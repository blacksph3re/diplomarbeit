import gym

from averager import Averager
from gradientclip import GradientClip
from differential_control import DifferentialControl
from coleman_transform import ColemanTransform
from mask import Mask
from meannormalizer import MeanNormalizer
from pastfeeder import Pastfeeder
from dilated_pastfeeder import DilatedPastfeeder
from client import Client
from windturbinerewards import WindturbineRewards
from trajectoryclip import TrajectoryClip
from rewardsdelay import RewardsDelay
from ignore_steps import IgnoreSteps
from windrandomizer import WindRandomizer
from freezeactions import FreezeActions
from polartransform import PolarTransform
from gramian_angular_field import GramianAngularField
from discretize_actions import DiscretizeActions
from extreme_load_classifier import ExtremeLoadClassifier
from hparams import HParams

def makeenv(hparams, log_writer=None):
  env = Client(hparams)
  # env = WindturbineRewards(env, hparams)
  if hparams.get_default('randomize_wind', False):
    env = WindRandomizer(env, hparams)
  if hparams.get_default('clip_action_gradients', True):
    env = GradientClip(env, hparams)
  if hparams.get_default('coleman_transform', False):
    assert hparams.get_default('differential_control', True) == False, 'Can not activate both coleman and differential control'
    assert hparams.get_default('clip_action_gradients', True) == False, 'Can not activate both coleman and action grad clipping'
    # assert hparams.mask_act.startswith('coleman'), 'Action masking should be coleman-related'
    env = ColemanTransform(env, hparams)
  if hparams.get_default('differential_control', True):
    env = DifferentialControl(env, hparams)
  if hparams.get_default('log_env', False):
    from .qbladelogger import QBladeLogger
    env = QBladeLogger(env, hparams, log_writer)
  if hparams.get_default('polar_transform', True):
    env = PolarTransform(env, hparams)
  if hparams.get_default('extreme_load_classifier', False):
    env = ExtremeLoadClassifier(env, hparams)
  if hparams.get_default('mean_normalizing', True):
    env = MeanNormalizer(env, hparams)
  if hparams.get_default('mask', True):
    env = Mask(env, hparams)
  if hparams.get_default('averaging', False):
    env = Averager(env, hparams)
  if hparams.get_default('log_masked', False):
    from .maskedlogger import MaskedLogger
    env = MaskedLogger(env, hparams, log_writer)
  if hparams.get_default('freeze_actions', False):
    env = FreezeActions(env, hparams)
  if hparams.get_default('past_feeding', False):
    env = Pastfeeder(env, hparams)
  if hparams.get_default('dilated_past_feeding', True):
    env = DilatedPastfeeder(env, hparams)
  if hparams.get_default('enable_ignore_steps', False):
    env = IgnoreSteps(env, hparams)
  if hparams.get_default('enable_gaf', False):
    env = GramianAngularField(env, hparams)
  if hparams.get_default('enable_trajectory_clip', False):
    env = TrajectoryClip(env, hparams)
  if hparams.get_default('delayed_rewards', False):
    assert 'max_trajectory_length' in hparams, 'Rewards delay without trajectory clipping can result in lost rewards'
    env = RewardsDelay(env)
  if hparams.get_default('enable_discretization', False):
    env = DiscretizeActions(env, hparams)
  
  return env
  
class WindturbineEnv(gym.Env):
  def __init__(self, hparams=None, log_writer=None):
    if hparams == None:
      hparams = HParams(
        log_env = False,
        log_masked = False,
      )
    
    self.env = makeenv(hparams, log_writer)

    self.action_space = self.env.action_space
    self.observation_space = self.env.observation_space
    self.metadata = self.env.metadata
  
  def reset(self):
    return self.env.reset()

  def step(self, action):
    return self.env.step(action)

  def close(self):
    return self.env.close()
  
  def render(self):
    return self.env.render()