"""Training, deterministic evaluation and replayable evidence. CPU only."""
import argparse,concurrent.futures,hashlib,json,os,pickle,random,signal,time
from pathlib import Path
import numpy as np
from .store import *
from .envs import FoodEnv,rule_action

def seed_digest(seeds):return hashlib.sha256(json.dumps(seeds).encode()).hexdigest()[:12]
def checkpoint(model,env,path,config):
    import torch
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.partial.zip');model.save(temp);os.replace(temp,str(path)+'.zip')
    rng={'python':random.getstate(),'numpy':np.random.get_state(),'torch':torch.get_rng_state(),'env':env.env_method('export_rng')}
    with open(str(path)+'.rng.pkl.tmp','wb') as f:pickle.dump(rng,f)
    os.replace(str(path)+'.rng.pkl.tmp',str(path)+'.rng.pkl')
    atomic(str(path)+'.json',{'at':now(),'timesteps':model.num_timesteps,'config':config,'normalization':'fixed observation divisors; no running statistics','resume_boundary':'new episode; partial on-policy rollout discarded','optimizer':'included in SB3 zip','gradient_updates':model._n_updates,'source_version':read(path.parents[2]/'source-version.json',{})})

def build_vec(config,workers):
    from stable_baselines3.common.vec_env import SubprocVecEnv,DummyVecEnv
    from functools import partial
    calls=[partial(FoodEnv,**{k:v for k,v in config.items() if k in ['backend','task','curriculum','reward_mode','max_steps']}) for _ in range(workers)]
    return SubprocVecEnv(calls,start_method='spawn') if workers>1 else DummyVecEnv(calls)

def train(run,config,steps,workers=1,resume=None,deadline=None):
    import torch
    torch.set_num_threads(1)
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    run=Path(run);preserve_source(run);trial=config['trial'];dest=run/'checkpoints'/trial;dest.mkdir(parents=True,exist_ok=True);env=build_vec(config,workers)
    stop={'value':False}
    def sig(*_):stop['value']=True
    signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
    env.seed(config['seed'])
    if resume:
        model=PPO.load(resume,env=env,device='cpu');rngpath=Path(str(resume).removesuffix('.zip')+'.rng.pkl')
        if rngpath.exists():
            with rngpath.open('rb') as f:rng=pickle.load(f)
            random.setstate(rng['python']);np.random.set_state(rng['numpy']);torch.set_rng_state(rng['torch'])
            for i,r in enumerate(rng['env']):env.env_method('restore_rng',r,indices=i)
            env._seeds=[None]*workers
        event(run,'resume','다음 에피소드부터 정책 학습 재개',trial=trial,checkpoint=str(resume),detail='정책·optimizer·난수 상태를 읽었습니다. 중단된 rollout은 폐기하고 새 에피소드에서 시작합니다.')
    else:model=PPO('MlpPolicy',env,seed=config['seed'],device='cpu',n_steps=128,batch_size=64,n_epochs=5,learning_rate=3e-4,gamma=.99,gae_lambda=.95,ent_coef=.01,policy_kwargs={'net_arch':[64,64]},verbose=0)
    started=time.time();initial=model.num_timesteps
    checkpoint(model,env,dest/f'step-{initial:09d}',config)
    class RecorderCallback(BaseCallback):
        def __init__(self):super().__init__();self.saved=time.time();self.beat=0;self.terms={}
        def _on_step(self):
            for info in self.locals.get('infos',[]):
                for k,v in info.get('reward_terms',{}).items():self.terms[k]=self.terms.get(k,0)+float(v)
            if time.time()-self.beat>10:
                self.beat=time.time();progress={'trial':trial,'timesteps':self.model.num_timesteps,'steps_this_segment':self.model.num_timesteps-initial,'decisions_per_second':(self.model.num_timesteps-initial)/max(.1,time.time()-started),'reward_terms_sum':self.terms,'checkpoint':asset(run,dest/f'step-{initial:09d}.zip')}
                update_state(run,status='training',backend=config['backend'],activity=f'{trial} 정책 학습',training=progress,result='정책을 업데이트하는 중입니다. 성능 판정은 분리된 평가 결과로 합니다.')
                atomic(run/'trainer-heartbeat.json',{'pid':os.getpid(),'at':now(),'epoch':time.time(),**progress})
            if time.time()-self.saved>=600:
                checkpoint(self.model,env,dest/f'step-{self.model.num_timesteps:09d}',config);self.saved=time.time();event(run,'checkpoint','10분 정책 체크포인트 저장',trial=trial,timesteps=self.model.num_timesteps)
            return not stop['value'] and not (deadline and time.time()>=deadline) and not (run/'STOP').exists()
    try:
        model.learn(total_timesteps=steps,reset_num_timesteps=False,callback=RecorderCallback())
        output=dest/f'step-{model.num_timesteps:09d}';checkpoint(model,env,output,config)
        result={'at':now(),'trial':trial,'checkpoint':str(output)+'.zip','timesteps':model.num_timesteps,'seconds':time.time()-started,'stopped':stop['value'],'config':config};atomic(run/'trials'/f'{trial}.json',result);event(run,'training','학습 구간 저장',**result);return result
    finally:env.close()

def eval_worker(args):
    config,seeds,policy,modelpath,video_path,progress_dir=args
    import torch
    torch.set_num_threads(1)
    model=None
    if modelpath:
        from stable_baselines3 import PPO
        model=PPO.load(modelpath,device='cpu')
    rows=[];env=None
    try:
        for j,seed in enumerate(seeds):
            capture=video_path is not None and j==0
            if env is None:env=FoodEnv(**{k:v for k,v in config.items() if k in ['backend','task','curriculum','reward_mode','max_steps']},render_mode='rgb_array' if capture else None)
            obs,info=env.reset(seed=seed);rng=np.random.default_rng(seed+4000000);total=0.;terms={};frames=[];error=None
            for step in range(config.get('max_steps',160)):
                if model:action,_=model.predict(obs,deterministic=True)
                elif policy=='rule':action=rule_action(obs)
                else:action=rng.uniform(-.5,1.5,2)
                try:obs,r,term,trunc,info=env.step(action)
                except Exception as exc:error=repr(exc);break
                total+=r
                if progress_dir and step%20==0:atomic(Path(progress_dir)/f'{seed}.json',{'seed':seed,'step':step+1,'status':'running','at':now(),'position':env.pos.tolist(),'distance':env.distance})
                for k,v in info['reward_terms'].items():terms[k]=terms.get(k,0)+v
                if capture:
                    frame=env.render()
                    if frame is not None:frames.append(frame.copy())
                if term or trunc:break
            row={'seed':seed,'success':bool(info.get('success',False)) and not error,'steps':step+1,'reward':total,'reward_terms':terms,'info':info,'error':error,'path':env.path,'actions':env.actions,'target':env.target.tolist(),'obstacle':env.obstacle.tolist() if config['task']=='obstacles' else None}
            if capture and frames:
                import imageio.v2 as imageio
                imageio.mimsave(video_path,frames,fps=20,macro_block_size=1);row['video_path']=video_path
            rows.append(row)
            if progress_dir:atomic(Path(progress_dir)/f'{seed}.json',{'seed':seed,'step':step+1,'status':'done','success':row['success'],'at':now(),'error':error})
            if capture:env.close();env=None
    finally:
        if env:env.close()
    return rows

def paths_plot(rows,path,title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,6));fig.patch.set_facecolor('#f7f8fa')
    for r in rows:
        p=np.array(r['path']);ax.plot(p[:,0],p[:,1],alpha=.5,color='#21906c' if r['success'] else '#cc6248');ax.scatter(*r['target'],marker='*',s=50,color='#21906c')
        if r.get('obstacle'):ax.add_patch(plt.Circle(r['obstacle'],1.2,color='#6f7882',alpha=.15))
    ax.scatter(0,0,color='#213546',s=50,label='Start');ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.set_xlabel('x (mm in 3D; proxy units in 2D)');ax.set_ylabel('y');ax.set_title(title);fig.tight_layout();fig.savefig(path,dpi=140);plt.close(fig)

def evaluate(run,config,policy='random',modelpath=None,seeds=None,workers=1,tag='fixed',timesteps=0):
    run=Path(run);source=preserve_source(run);timesteps=read(str(modelpath).removesuffix('.zip')+'.json',{}).get('timesteps',timesteps) if modelpath else timesteps;seeds=seeds or list(range(10000,10020));stamp=f'{time.time_ns()}-{config["trial"]}-{policy}-{tag}';video=run/'media'/f'{stamp}.mp4';path=run/'media'/f'{stamp}-paths.png'
    event(run,'evaluation','동일 조건 행동 평가 시작',trial=config['trial'],policy=policy,seeds=seeds,backend=config['backend'],task=config['task'],command=f'.venv/bin/python -m lab.learning evaluate {run} --config {run}/configs/{config["trial"]}.json --policy {policy}'+(f' --checkpoint {modelpath}' if modelpath else '')+f' --seed-start {seeds[0]} --episodes {len(seeds)} --workers {workers}',command_ko='학습에 쓰지 않은 고정 시작 조건에서 먹이 도달 횟수를 셉니다. 모델을 평가 중에 업데이트하지 않습니다.')
    update_state(run,status='evaluating',backend=config['backend'],activity=f'{policy} {len(seeds)}회 평가',question='같은 시작 조건에서 이전보다 먹이에 더 잘 도착할까?',result=f'{policy} 정책의 {len(seeds)}개 고정 조건을 평가 중입니다. 아직 최종 집계 전입니다.',next_action='모든 에피소드를 마친 뒤 성공·실패·경로와 영상을 저장')
    tasks=[]
    for i in range(min(workers,len(seeds))):tasks.append((config,seeds[i::workers],policy,modelpath,str(video) if i==0 else None,str(run/'evaluation-progress'/stamp)))
    start=time.time()
    if workers==1:rows=eval_worker(tasks[0])
    else:
        import multiprocessing as mp
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:rows=[r for batch in pool.map(eval_worker,tasks) for r in batch]
    rows.sort(key=lambda r:r['seed']);paths_plot(rows,path,f'{config["backend"]} / {config["curriculum"]} / {policy} / {timesteps} steps')
    record=run/'evaluations'/f'{stamp}.json';n=len(rows);success=sum(r['success'] for r in rows);out={'id':stamp,'evaluated_at':now(),'backend':config['backend'],'task':config['task']+'-'+config['curriculum'],'policy':policy,'policy_family':config['trial'] if modelpath else policy,'trial':config['trial'],'seed':config['seed'],'timesteps':timesteps,'success_rate':success/n,'successes':success,'episodes':n,'mean_steps':float(np.mean([r['steps'] for r in rows])),'mean_success_seconds':float(np.mean([r['steps']*.05 for r in rows if r['success']])) if success else None,'collision_count':sum(r['info'].get('collisions',0) for r in rows),'flip_count':sum(r['info'].get('flips',0) for r in rows),'seconds':time.time()-start,'evaluation_suite':seed_digest(seeds),'selection_holdout':tag=='holdout','seeds':seeds,'progress_dir':asset(run,run/'evaluation-progress'/stamp),'checkpoint':asset(run,Path(modelpath)) if modelpath and Path(modelpath).is_relative_to(run) else modelpath,'config':config,'video':asset(run,video) if video.exists() else None,'video_seed':seeds[0],'path_image':asset(run,path),'record_url':asset(run,record),'episodes_raw':rows,'source_version':source,'checkpoint_sha256':hashlib.sha256(Path(modelpath).read_bytes()).hexdigest() if modelpath else None}
    atomic(record,out);atomic(run/'latest-evaluation.json',out);event(run,'result',f'{config["backend"]} {policy}: {success}/{n}회 먹이 도달',evaluation=out['record_url'],success_rate=out['success_rate'],seconds=out['seconds']);update_state(run,result=f'{config["backend"]} {policy}: 동일 조건 {n}회 중 {success}회 도달. 학습량 {timesteps:,}회.');publish(run);return out

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['train','evaluate']);p.add_argument('run');p.add_argument('--config',required=True);p.add_argument('--steps',type=int,default=2048);p.add_argument('--workers',type=int,default=1);p.add_argument('--checkpoint');p.add_argument('--policy',default='ppo');p.add_argument('--seed-start',type=int,default=10000);p.add_argument('--episodes',type=int,default=20);p.add_argument('--tag',default='fixed');p.add_argument('--deadline',type=float);a=p.parse_args();config=read(a.config)
    if a.mode=='train':out=train(Path(a.run).resolve(),config,a.steps,a.workers,a.checkpoint,a.deadline)
    else:out=evaluate(Path(a.run).resolve(),config,a.policy,a.checkpoint,list(range(a.seed_start,a.seed_start+a.episodes)),a.workers,a.tag)
    print(json.dumps({k:v for k,v in out.items() if k!='episodes_raw'},ensure_ascii=False))
if __name__=='__main__':main()
