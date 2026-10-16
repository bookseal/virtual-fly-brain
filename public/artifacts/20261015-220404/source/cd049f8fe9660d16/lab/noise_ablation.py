"""Predeclared one-factor experiment: initial Gaussian exploration scale only."""
import argparse,os,signal,subprocess,time
from pathlib import Path
from .store import *
from .manage import matching
from .campaign import latest_checkpoint


def job(run,args,deadline):
    # A bounded compatibility probe can borrow these two worker slots between
    # jobs; never interrupt or overlap an already running rollout/evaluation.
    while (run/'PAUSE_NOISE').exists():
        if time.time()>=deadline or (run/'STOP').exists():return False
        if time.time()>=read(run/'PAUSE_NOISE',{}).get('expires_epoch',0):
            (run/'PAUSE_NOISE').unlink(missing_ok=True)
            event(run,'maintenance','호환성 측정 대기 시간 종료 · 보조 비교 재개')
            break
        time.sleep(3)
    command=[str(ROOT/'.venv/bin/python'),'-m','lab.learning',*map(str,args)]
    path=run/'logs'/f'noise-ablation-{time.time_ns()}.log'
    event(run,'command','초기 탐험 폭 변경 실험',command=' '.join(command),command_ko='주 비교와 다른 trial에 저장합니다. 초기 탐험 폭 외의 학습 조건은 유지합니다.')
    with path.open('w') as log:
        proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        atomic(run/'noise-ablation-job.json',{'pid':proc.pid,'command':command,'at':now()})
        while proc.poll() is None:
            if time.time()>=deadline or (run/'STOP').exists():
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=30)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                return False
            time.sleep(3)
    if proc.returncode:raise RuntimeError(f'Noise experiment failed: {path.name}')
    return True


def initial_equivalence(run,new,original):
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(1)
    a=PPO.load(original).policy.state_dict();b=PPO.load(new).policy.state_dict()
    equal=all(torch.equal(a[k],b[k]) for k in a if k!='log_std')
    if not equal:raise RuntimeError('Initial policy weights differ beyond log_std')
    return {'all_other_parameters_identical':True,'original_log_std':a['log_std'].tolist(),'variant_log_std':b['log_std'].tolist(),'original_checkpoint':asset(run,original),'variant_checkpoint':asset(run,new),'note':'결정적 평가의 평균 행동은 동일합니다. 새 20회 평가를 실행했다고 표현하지 않고 기존 초기 평가를 참조합니다.'}


def finish(run,status,**extra):
    atomic(run/'noise-ablation.json',{'status':status,'at':now(),**extra});publish(run)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();run=Path(a.run).resolve();end=read(run/'run.json')['started_epoch']+23.5*3600
    with lock(run/'.noise-ablation.lock'):
        atomic(run/'noise-ablation.json',{'status':'waiting_for_diagnostic_workers','at':now(),'pid':os.getpid(),'initial_log_std':-1.,'seeds':[11,29],'arms':['control','small'],'protocol':'seeded-rng-v2','online_budget_per_seed':10240,'holdout_seed_start':92000,'deadline_epoch':end})
        # Two primary workers + two supplementary workers is the global maximum.
        while read(run/'generalization.json',{}).get('status')=='running':
            if time.time()>end or (run/'STOP').exists():return finish(run,'stopped',reason='deadline or STOP')
            pid=read(run/'generalization-process.json',{}).get('pid')
            if not matching(pid,'lab.generalization',run):return finish(run,'blocked',reason='Diagnostic runner disappeared; inspect children before taking worker slots')
            time.sleep(10)
        try:
            arms=[(seed,arm,std) for seed in (11,29) for arm,std in [('control',0.),('small',-1.)]]
            # Complete both arms at the early boundary before extending any
            # one arm. Holdout observations stay last, after all fixed budgets.
            for target in (2048,10240):
                for seed,arm,initial_std in arms:
                    if read(run/'quota.json',{}).get('gate')!='continue':return finish(run,'budget_limit')
                    trial=f'3d-near-noise-v2-{arm}-seed{seed}'
                    policy='ppo-noise-control' if arm=='control' else 'ppo-low-noise'
                    c=read(run/'configs'/f'3d-near-ppo-seed{seed}.json');c.update(trial=trial,initial_log_std=initial_std,training_rng_protocol='explicit-seed-before-checkpoint-v2',purpose='one-factor initial exploration ablation with fresh seeded control')
                    config=run/'configs'/f'{trial}.json';atomic(config,c)
                    atomic(run/'noise-ablation.json',{'status':'running','at':now(),'trial':trial,'initial_log_std':initial_std,'arm':arm,'protocol':'seeded-rng-v2','current_target':target,'online_budget_per_seed':10240,'holdout_seed_start':92000,'deadline_epoch':end})
                    cp=latest_checkpoint(run,trial)
                    if not cp:
                        if not job(run,['train',run,'--config',config,'--workers','2','--steps','0','--background-training'],end):return finish(run,'stopped',reason='deadline or STOP')
                        cp=latest_checkpoint(run,trial)
                        original=run/'checkpoints'/(f'3d-near-noise-v2-control-seed{seed}' if arm=='small' else f'3d-near-ppo-seed{seed}')/'step-000000000.zip'
                        proof=initial_equivalence(run,cp,original)
                        import pickle,numpy as np
                        with Path(str(cp).removesuffix('.zip')+'.rng.pkl').open('rb') as f:rng=pickle.load(f)
                        proof['environment_rng_matches_declared_seeds']=all(state==np.random.default_rng(seed+i).bit_generator.state for i,state in enumerate(rng['env']))
                        if not proof['environment_rng_matches_declared_seeds']:raise RuntimeError('Initial environment RNG mismatch')
                        atomic(run/'trials'/f'{trial}-initial-equivalence.json',proof)
                    while (steps:=read(str(cp).removesuffix('.zip')+'.json')['timesteps'])<target:
                        if read(run/'quota.json',{}).get('gate')!='continue':return finish(run,'budget_limit')
                        if not job(run,['train',run,'--config',config,'--workers','2','--steps',min(2048,target-steps),'--checkpoint',cp,'--deadline',end,'--background-training'],end):return finish(run,'stopped',reason='deadline or STOP')
                        cp=latest_checkpoint(run,trial)
                    existing=[read(p) for p in (run/'evaluations').glob('*.json') if read(p).get('trial')==trial and read(p).get('timesteps')==target and not read(p).get('selection_holdout')]
                    if not existing and not job(run,['evaluate',run,'--config',config,'--workers','2','--checkpoint',cp,'--policy',policy,'--background-evaluation'],end):return finish(run,'stopped',reason='deadline or STOP')
            for seed,arm,_ in arms:
                if read(run/'quota.json',{}).get('gate')!='continue':return finish(run,'budget_limit')
                trial=f'3d-near-noise-v2-{arm}-seed{seed}';config=run/'configs'/f'{trial}.json';cp=latest_checkpoint(run,trial)
                policy='ppo-noise-control' if arm=='control' else 'ppo-low-noise'
                atomic(run/'noise-ablation.json',{'status':'running','at':now(),'trial':trial,'phase':'final_holdout','protocol':'seeded-rng-v2','online_budget_per_seed':10240,'holdout_seed_start':92000,'deadline_epoch':end})
                completed_holdout=any((e:=read(p,{})).get('trial')==trial and e.get('selection_holdout') and e.get('timesteps')==10240 for p in (run/'evaluations').glob('*.json'))
                if not completed_holdout and not job(run,['evaluate',run,'--config',config,'--workers','2','--checkpoint',cp,'--policy',policy,'--seed-start','92000','--episodes','30','--tag','holdout','--background-evaluation'],end):return finish(run,'stopped',reason='deadline or STOP')
            atomic(run/'noise-ablation.json',{'status':'completed','at':now(),'note':'실제 완료한 trial과 평가 수는 원본 결과에서 확인합니다.'});publish(run)
        except Exception as exc:
            atomic(run/'noise-ablation.json',{'status':'blocked','at':now(),'error':str(exc)});event(run,'error','탐험 폭 변경 실험 보류',detail=str(exc));publish(run)
if __name__=='__main__':main()
