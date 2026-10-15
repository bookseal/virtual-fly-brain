"""Replay recorded actions; report exact evidence differences, never overwrite evaluation."""
import argparse,time
from pathlib import Path
import numpy as np
from .store import *
from .envs import FoodEnv,env_options

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('--evaluation',required=True);ap.add_argument('--seed',type=int);ap.add_argument('--limit',type=int,default=0);a=ap.parse_args();run=Path(a.run).resolve();record=read(a.evaluation);episode=next(r for r in record['episodes_raw'] if a.seed is None or r['seed']==a.seed);c=record['config'];env=FoodEnv(**env_options(c));obs,_=env.reset(seed=episode['seed']);model=None;action_error=0.
    if record.get('checkpoint'):
        import torch
        from stable_baselines3 import PPO
        torch.set_num_threads(1);cp=Path(record['checkpoint']);cp=cp if cp.is_absolute() else ROOT/'site'/cp;model=PPO.load(cp,device='cpu')
    actions=episode.get('policy_actions',episode['actions'])[:a.limit or None];start=time.time()
    for action in actions:
        if model:
            predicted,_=model.predict(obs,deterministic=True);action_error=max(action_error,float(np.max(np.abs(predicted-action))));action=predicted
        obs,_,_,_,_=env.step(action)
    actual=np.array(env.path);expected=np.array(episode['path'][:len(actual)]);error=float(np.max(np.abs(actual-expected)));out={'at':now(),'evaluation':str(a.evaluation),'seed':episode['seed'],'steps':len(actions),'full_episode':len(actions)==len(episode['actions']),'max_position_error':error,'within_1e-5':error<=1e-5 and action_error<=1e-5,'checkpoint_recomputed':model is not None,'max_action_error':action_error,'seconds':time.time()-start,'source_version':read(run/'source-version.json',{})};env.close();atomic(run/'replay'/f'{time.time_ns()}.json',out);event(run,'verification','저장한 행동과 seed로 실제 경로 재생 검증',**out);print(out)
if __name__=='__main__':main()
