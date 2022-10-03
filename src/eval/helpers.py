import pickle
import numpy as np
import itertools
import pandas as pd
import plotly.express as px
import plotly
import plotly.graph_objs as go

import matplotlib.pyplot as plt
import scipy

import lzma
import os
import re
import json
import rainflow

import sys
sys.path.insert(1, '/home/sph3re/Programming/windturbine/src/env')
import hparams

def calc_del(signal, dt=0.1, fdel=1, m=1, skip=300, bin=True):
    signal = signal[skip:]

    rainflow_data = np.array(rainflow.count_cycles(signal, nbins=(128 if bin else None)))
    
    # rainflow_data = np.array(list(rainflow.extract_cycles(signal)))
    # lm = rainflow_data[:,1]

    lr = rainflow_data[:,0]
    n = rainflow_data[:,1]

    # lrf = lr * ((lult - np.abs(lmf)) / (lult - np.abs(lm)))
    lrf = lr

    T = len(signal)*dt
    nsteq = fdel*T

    delst = (np.sum(np.sum(n * lrf ** m)) / np.sum(nsteq)) ** (1/m)
    return delst


def calc_extreme(signal, skip=300, q=0.99):
  return np.quantile(signal[skip:], q)

def iqm(arr, axis=None):
    arr = np.array(arr)
    if axis is None:
        arr = np.sort(arr.flatten())
        return arr[int(len(arr)*0.25):int(np.ceil(len(arr)*0.75))].mean()
        
    arr = np.sort(arr, axis=axis)
    idx_start = int(arr.shape[axis]*0.25)
    idx_end = int(np.ceil(arr.shape[axis]*0.75))
    return np.mean(np.take(arr, range(idx_start, idx_end), axis=axis), axis=axis)

def calc_del_episodes(data):
    retval = {'DEL1': calc_del(data['oop blade root bending moment blade 1 [N]'], m=10, skip=300),
        'DEL2': calc_del(data['oop blade root bending moment blade 2 [N]'], m=10, skip=300),
        'DEL3': calc_del(data['oop blade root bending moment blade 3 [N]'], m=10, skip=300),
        'pDEL1': calc_del(data['pitch blade 1 [deg]'], m=1, skip=300),
        'pDEL2': calc_del(data['pitch blade 2 [deg]'], m=1, skip=300),
        'pDEL3': calc_del(data['pitch blade 3 [deg]'], m=1, skip=300),
        'extreme1': calc_extreme(data['oop blade root bending moment blade 1 [N]'], q=0.99, skip=300),
        'extreme2': calc_extreme(data['oop blade root bending moment blade 2 [N]'], q=0.99, skip=300),
        'extreme3': calc_extreme(data['oop blade root bending moment blade 3 [N]'], q=0.99, skip=300),
        'power': np.mean(data['power [W]'][300:]),
        'pitch_travel': np.mean(np.mean(np.abs(np.diff(data[["pitch blade 1 [deg]", "pitch blade 2 [deg]", "pitch blade 3 [deg]"]], axis=1)), axis=1)*10)
    }

    retval['DEL'] = np.mean([retval['DEL1'], retval['DEL2'], retval['DEL3']])
    retval['pDEL'] = np.mean([retval['pDEL1'], retval['pDEL2'], retval['pDEL3']])
    retval['extreme'] = np.mean([retval['extreme1'], retval['extreme2'], retval['extreme3']])
    return retval

def get_column_names(hparams):
    orig_state_columns = ["rotational speed [rad/s]", 
    "power [W]", 
    "HH wind velocity [m/s]", 
    "yaw angle [deg]", 
    "pitch blade 1 [deg]", 
    "pitch blade 2 [deg]", 
    "pitch blade 3 [deg]", 
    "oop blade root bending moment blade 1 [N]", 
    "oop blade root bending moment blade 2 [N]", 
    "oop blade root bending moment blade 3 [N]", 
    "ip blade root bending moment blade 1 [N]", 
    "ip blade root bending moment blade 2 [N]", 
    "ip blade root bending moment blade 3 [N]", 
    "tor blade root bending moment blade 1 [Nm]", 
    "tor blade root bending moment blade 2 [Nm]", 
    "tor blade root bending moment blade 3 [Nm]", 
    "oop tip deflection blade 1 [m]", 
    "oop tip deflection blade 2 [m]", 
    "oop tip deflection blade 3 [m]", 
    "ip tip deflection blade 1 [m]", 
    "ip tip deflection blade 2 [m]", 
    "ip tip deflection blade 3 [m]", 
    "tower top acceleration in global X [m^2/s]",
    "tower top acceleration in global Y [m^2/s]",
    "tower top acceleration in global Z [m^2/s]",
    "tower bottom bending moment along global X [Nm]",
    "tower bottom bending moment along global Y [Nm]",
    "tower bottom bending moment along global Z [Nm]",
    "current time [s]",
    "azimuthal position of the LSS [deg]",
    "azimuthal position of the HSS [deg]",
    "HSS torque [Nm]",
    "wind speed at hub height [m/s]",
    "horizontal inflow angle [deg]",
    "tower top fore aft acceleration [m/s^2]",
    "tower top side side acceleration [m/s^2]",
    "tower top X position [m]",
    "tower top Y position [m]",
    "controller torque [N]",
    "controller pitch 1 [deg]",
    "controller pitch 2 [deg]",
    "controller pitch 3 [deg]"]
    
    state_columns = orig_state_columns
    if hparams and "coleman_transform" in hparams and hparams["coleman_transform"]:
        if hparams and "coleman_s_to_obs" in hparams and hparams["coleman_s_to_obs"]:
            state_columns = list(np.append(state_columns, ["coleman transformed bending moments s"]))
        state_columns = list(np.append(state_columns, ["coleman transformed bending moments d", "coleman transformed bending moments q"]))
    if hparams and "polar_transform" in hparams and "polar_transform_lss" in hparams and hparams["polar_transform_lss"]:
        state_columns = list(np.append(state_columns, ["polar transformed LSS position [x]", "polar transformed LSS position [y]"]))
    if hparams and "polar_transform" in hparams and "polar_transform_hss" in hparams and hparams["polar_transform_hss"]:
        state_columns = list(np.append(state_columns, ["polar transformed LSS position [x]", "polar transformed LSS position [y]"]))

    if hparams and "mask" in hparams and hparams["mask"] and "mask_obs" in hparams:
        state_columns = list(np.array(state_columns)[hparams["mask_obs"]])
    if hparams and "dilated_past_feeding" in hparams and hparams["dilated_past_feeding"]:
        new_columns = []
        for i in range(hparams["dilated_past_feeding_steps"]):
            tmp_columns = [x + " p%d" % i for x in state_columns]
            new_columns.append(tmp_columns)
        state_columns = list(itertools.chain(*new_columns))

    orig_action_columns = ["torque", "pitch_1", "pitch_2", "pitch_3"]
    coleman_action_columns = ["torque", "S", "D", "Q", "Phi_lead"]
    action_columns = orig_action_columns
    if hparams and "mask" in hparams and hparams["mask"] and "mask_act" in hparams:
        if hparams["mask_act"] == "individual-pitch-no-torque":
            action_columns = ["pitch_1", "pitch_2", "pitch_3"]
        elif hparams["mask_act"] == "collective_pitch":
            action_columns = ["torque", "pitch"]
        elif 'coleman_transform' in hparams and hparams['coleman_transform']:
            action_columns = np.array(coleman_action_columns)[hparams['mask_act_parsed']]
    
    return state_columns, action_columns, orig_state_columns, orig_action_columns


def sum_azimuths(states):
    tmp = states['azimuthal position of the LSS [deg]'].copy()
    offset = 0
    for index in range(1,len(tmp)):
        if states['azimuthal position of the LSS [deg]'][index-1] > tmp[index]:
            offset += 360
        tmp[index] += offset
    states['azimuthal position of the LSS sum [deg]'] = tmp
    return states

def parse_data(episode_idx, data, deterministic=True):
    if deterministic:
        episodes = data['episodes']
    else:
        episodes = data['episodes_nondeterministic']

    state_columns, action_columns, orig_state_columns, orig_action_columns = get_column_names(data['hparams'])
    obs = pd.DataFrame(episodes.observations_list[episode_idx], columns=state_columns)
    act = pd.DataFrame(episodes.actions_list[episode_idx], columns=action_columns)

    if episode_idx == 0:
        start_idx = 0
    else:
        start_idx = sum(episodes.lengths[0:episode_idx])
    end_idx = start_idx + episodes.lengths[episode_idx]
    start_idx, end_idx

    controller_actions = pd.DataFrame(np.stack(episodes.env_infos['env_info']['controller_action'][start_idx:end_idx]), columns=orig_action_columns)
    orig_actions = pd.DataFrame(episodes.env_infos['orig_action'][start_idx:end_idx], columns=orig_action_columns)
    orig_states = pd.DataFrame(episodes.env_infos['orig_state'][start_idx:end_idx,0:len(orig_state_columns)], columns=orig_state_columns)

    if 'reward_composition' in episodes.env_infos:
        reward_composition = pd.DataFrame(episodes.env_infos['reward_composition'])[start_idx:end_idx]
        reward_composition['reward'] = episodes.rewards[start_idx:end_idx]
        reward_composition = np.clip(reward_composition, -data['hparams']['reward_clip'], data['hparams']['reward_clip'])
    else:
        reward_composition = {}

    act_mean = pd.DataFrame(episodes.agent_infos['mean'][start_idx:end_idx], columns=action_columns)
    act_logstd = pd.DataFrame(episodes.agent_infos['log_std'][start_idx:end_idx], columns=action_columns)

    # Add column to orig states with total rotation, useful for plotting
    orig_states = sum_azimuths(orig_states)
    stats = calc_del_episodes(orig_states)

    ipc_reference = None
    ipc_stats = None
    if deterministic and "config_groups" in data:
        ipc_reference = load_ipc_reference(data['config_groups'][episode_idx])
        if ipc_reference is not None:
            ipc_stats = calc_del_episodes(ipc_reference)
    
    q = data.get('q' if deterministic else 'q_nondeterministic', None)
    if q is not None and len(q)>=episode_idx and q[episode_idx] is not None:
        q = pd.DataFrame(np.array(q[episode_idx]), columns=['qf1', 'qf2'])
    else:
        q = pd.DataFrame()

    reward = np.array(episodes.rewards[start_idx:end_idx])
    gamma_list = np.array([data['hparams']['discount']**(i) for i in range(len(reward))])

    value = [np.sum(reward * gamma_list)]
    value = value + [np.sum(reward[i:]*gamma_list[:-i]) for i in range(1, len(reward))]
    q['value'] = value


    entropy = np.sum(0.5 + 0.5 * np.log(2 * np.pi) + np.array(act_logstd), axis=1)
    q['entropy'] = entropy

    # logprobs = np.sum(-((np.array(act) - np.array(act_mean)) ** 2) / (2 * np.exp(np.array(act_logstd))**2) - np.array(act_logstd) - np.log(np.sqrt(2 * np.pi)), axis=1)
    # q['logprobs'] = logprobs

    entropy_disc = [np.sum(entropy * gamma_list)]
    entropy_disc = entropy_disc + [np.sum(entropy[i:]*gamma_list[:-i]) for i in range(1, len(entropy))]
    q['entropy_disc'] = entropy_disc

    q['sac_value'] = value - np.exp(data['hparams'].get('target_entropy', 0.01)) * np.array(entropy_disc)

    # logprobs_disc = [np.sum(logprobs * gamma_list)]
    # logprobs_disc = logprobs_disc + [np.sum(logprobs[i:]*gamma_list[:-i]) for i in range(1, len(logprobs))]
    # q['logprobs_disc'] = logprobs_disc

    
    return {
        "obs": obs,
        "act": act,
        "q": q,
        "controller_actions": controller_actions,
        "orig_actions": orig_actions,
        "orig_states": orig_states,
        "stats": stats,
        "reward_composition": reward_composition,
        "act_mean": act_mean,
        "act_logstd": act_logstd,
        "ipc_reference": ipc_reference,
        "ipc_stats": ipc_stats
    }


def find_reference(config_group, reference_dirs = None, base_dir='../../results/baselines/'):
    if reference_dirs is None:
        reference_dirs = [d for d in os.listdir(base_dir) if 'ipc' in d]

    if not isinstance(reference_dirs, list):
        reference_dirs = [reference_dirs]

    for d in reference_dirs:
        d = os.path.join(base_dir, d)
        references = [x for x in os.listdir(d) if x.startswith('reward_data_%d_' % config_group)]
        if len(references):
            return (d, references[0])
    return None

def load_ipc_reference(config_group, reference_dirs=None, base_dir='../../results/baselines/'):
    reference = find_reference(config_group, reference_dirs)
    if not reference:
        return None
    reference_dir, file = reference
    if file.endswith('.pkl'):
        with open(os.path.join(reference_dir, file), 'rb') as f:
            reference = pickle.load(f)
    elif file.endswith('.xz'):
        with lzma.open(os.path.join(reference_dir, file), 'rb') as f:
            reference = pickle.load(f)
    else:
        raise "unknown file extension"
    ref_state_names, _, _, _ = get_column_names(reference['hparams'])
    retval = pd.DataFrame(reference['states'][0], columns=ref_state_names)
    retval = sum_azimuths(retval)
    retval['reward'] = list(reference['rewards'].loc[0])
    return retval



def load_summary(folder):
    data = pd.read_csv(os.path.join(folder, 'summary.csv'))
    if 'iteration' in data.keys():
        data['iteration'] = data['iteration'].apply(int)
    if 'TotalEnvSteps' in data.keys():
        data['environment interactions'] = data['TotalEnvSteps'].apply(int)
   
    if 'DEL1' in data.keys() and 'DEL2' in data.keys() and 'DEL3' in data.keys():
        data['DEL'] = np.mean(data[['DEL1', 'DEL2', 'DEL3']], axis=1)
    if 'pDEL1' in data.keys() and 'pDEL2' in data.keys() and 'pDEL3' in data.keys():
        data['pDEL'] = np.mean(data[['pDEL1', 'pDEL2', 'pDEL3']], axis=1)
    if 'extreme1' in data.keys() and 'extreme2' in data.keys() and 'extreme3' in data.keys():
        data['extreme'] = np.mean(data[['extreme1', 'extreme2', 'extreme3']], axis=1)

    if 'group' in data.keys():
        groups = data['group'].unique()
        groups = [(g, load_ipc_reference(g)) for g in groups]
        groups = dict([(g, calc_del_episodes(data)) for (g, data) in groups if data is not None])
        def calc_rel_del(row, key='DEL'):
            if key in row and row['group'] in groups and groups[row['group']][key]>0.01:
                return row[key] / groups[row['group']][key]
            return np.nan
        
        if 'DEL' in data.keys():
            data['relDEL'] = data.apply(lambda row: calc_rel_del(row, 'DEL'), axis=1)
            data['w=0'] = data['relDEL']
        if 'pDEL' in data.keys():
            data['relpDEL'] = data.apply(lambda row: calc_rel_del(row, 'pDEL'), axis=1)
            data['w=1'] = data['relpDEL']
        if 'extreme' in data.keys():
            data['relextreme'] = data.apply(lambda row: calc_rel_del(row, 'extreme'), axis=1)
        if 'relDEL' in data.keys() and 'relpDEL' in data.keys():
            cost_factor = 0.5 # Tradeoff factor between pitch and blade DELs, 1/(2*5) means for every 1% blade DEL reduction we can torerate 5% pitch DEL increase
            data['weightedDEL'] = ((1-cost_factor)*data['relDEL'] + cost_factor*data['relpDEL'])
            data['w=0.5'] = data['weightedDEL']
        if 'power' in data.keys():
            data['relpower'] = data.apply(lambda row: calc_rel_del(row, 'power'), axis=1)

    try:
        with open(os.path.join(folder, 'global_hparams.json'), 'r') as f:
            hparams = json.load(f)
        for key, value in hparams.items():
            if key not in data.keys():
                data[key] = [value for _ in range(len(data))]
    except Exception as e:
        pass
    
    no_deaths = (data.groupby(['folder', 'iteration'])['lengths'].min() == data['lengths'].max()).to_frame().reset_index().rename(columns={'lengths': 'no_deaths'})
    data = data.merge(no_deaths, on=['folder', 'iteration'], how='left')

    return data