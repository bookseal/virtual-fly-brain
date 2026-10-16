"""Rule demonstrations and supervised policy initialization, separately accounted."""
import argparse,concurrent.futures,multiprocessing as mp,time,hashlib
from pathlib import Path
import numpy as np
from .store import *
from .envs import FoodEnv,env_options,teacher_action
from .learning import build_vec,checkpoint

def collect_worker(args):
    run,config,seeds=args;run=Path(run);env=FoodEnv(**env_options(config));summary=[]
    try:
        for seed in seeds:
            path=run/'demonstrations'/f'{seed}.npz'
            if path.exists():continue
            obs,_=env.reset(seed=seed);observations=[];actions=[]
            for step in range(config['max_steps']):
                action=teacher_action(env,obs);observations.append(obs.copy());actions.append(action.copy())
                obs,_,term,trunc,info=env.step(action)
                if term or trunc:break
            path.parent.mkdir(exist_ok=True)
            temporary=path.with_name(path.stem+'.partial.npz');np.savez_compressed(temporary,observations=observations,actions=actions,seed=seed,success=info['success']);temporary.replace(path)
            summary.append({'seed':seed,'samples':len(actions),'success':info['success']})
    finally:env.close()
    return summary

def collect(run,config,workers=2,episodes=200):
    start=time.time();seeds=list(range(200000,200000+episodes));validation=list(range(210000,210020))
    event(run,'decision','규칙 제어 시범 수집 시작',episodes=episodes,validation_episodes=20,training_seeds=seeds,validation_seeds=validation,detail='시범은 실제 3D 몸에서 수집합니다. 평가 seed와 겹치지 않습니다.')
    tasks=[(str(run),config,(seeds+validation)[i::workers]) for i in range(workers)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:list(pool.map(collect_worker,tasks))
    records=[]
    for seed in seeds+validation:
        with np.load(run/'demonstrations'/f'{seed}.npz') as z:records.append({'seed':seed,'samples':len(z['actions']),'success':bool(z['success'])})
    result={'at':now(),'backend':config['backend'],'train_seeds':seeds,'validation_seeds':validation,'episodes':records,'total_actions':sum(r['samples'] for r in records),'seconds':time.time()-start,'source':'rule controller actual rollouts'}
    atomic(run/'demonstrations/manifest.json',result);event(run,'result','규칙 시범 수집 완료',samples=result['total_actions'],seconds=result['seconds']);return result

def clone(run,config,epochs=80):
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(1);torch.manual_seed(config['seed']);rng=np.random.default_rng(config['seed']);start=time.time()
    manifest=read(run/'demonstrations/manifest.json')
    def dataset(seeds):
        observations=[];actions=[]
        for seed in seeds:
            with np.load(run/'demonstrations'/f'{seed}.npz') as z:observations.extend(z['observations']);actions.extend(z['actions'])
        return torch.tensor(np.array(observations),dtype=torch.float32),torch.tensor(np.array(actions),dtype=torch.float32)
    x,y=dataset(manifest['train_seeds']);vx,vy=dataset(manifest['validation_seeds'])
    env=build_vec({**config,'backend':'2d'},1)
    # Same spaces/network, no 2D rollout: only recorded 3D demonstrations train this policy.
    model=PPO('MlpPolicy',env,seed=config['seed'],device='cpu',n_steps=128,batch_size=64,n_epochs=5,learning_rate=3e-4,gamma=.99,gae_lambda=.95,ent_coef=.01,policy_kwargs={'net_arch':[64,64]},verbose=0)
    history=[]
    try:
        for epoch in range(epochs):
            for inds in np.array_split(rng.permutation(len(x)),max(1,len(x)//64)):
                predicted=model.policy.get_distribution(x[inds]).distribution.mean
                loss=torch.nn.functional.mse_loss(predicted,y[inds]);model.policy.optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.policy.parameters(),.5);model.policy.optimizer.step()
            if epoch%5==0 or epoch==epochs-1:
                with torch.no_grad():mse=float(torch.nn.functional.mse_loss(model.policy.get_distribution(vx).distribution.mean,vy))
                history.append({'epoch':epoch+1,'validation_mse':mse})
        # PPO starts with fresh optimizer moments, preserving only the learned policy weights.
        model.policy.optimizer.state.clear()
        dest=run/'checkpoints'/config['trial']/'step-000000000';checkpoint(model,env,dest,config)
        # RNG restoration is only defined for the same worker count; BC has no online env state.
        (Path(str(dest)+'.rng.pkl')).unlink()
        result={'at':now(),'trial':config['trial'],'checkpoint':str(dest)+'.zip','epochs':epochs,'train_samples':len(x),'validation_samples':len(vx),'history':history,'online_timesteps':0,'seconds':time.time()-start,'demonstration_manifest':asset(run,run/'demonstrations/manifest.json'),'initialization':'behavior-cloning-from-rule'}
        atomic(run/'trials'/f'{config["trial"]}-imitation.json',result);event(run,'result','시범 모방 초기화 완료 · 실제 평가로 확인 필요',trial=config['trial'],train_samples=len(x),validation_mse=history[-1]['validation_mse']);return result
    finally:env.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['collect','clone']);ap.add_argument('run');ap.add_argument('--config',required=True);ap.add_argument('--workers',type=int,default=2);ap.add_argument('--episodes',type=int,default=200);a=ap.parse_args();run=Path(a.run).resolve();c=read(a.config)
    print(collect(run,c,a.workers,a.episodes) if a.mode=='collect' else clone(run,c),flush=True)
if __name__=='__main__':main()
