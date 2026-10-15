"""Session-independent, bounded experiment schedule. No paid API/model calls.
All automated decisions use explicit rules and are attributed to local-script.
"""
import argparse,datetime as dt,os,signal,subprocess,time,traceback
from pathlib import Path
from .store import *
PYTHON=ROOT/'.venv/bin/python'

def alive(pid):
    try:os.kill(pid,0);return True
    except (ProcessLookupError,TypeError):return False

def review(run):
    state=read(run/'state.json',{});q=read(run/'quota.json',{});rows=[read(p) for p in sorted((run/'evaluations').glob('*.json'))];last=rows[-1] if rows else None
    out={'at':now(),'actor':'local-script','method':'predefined-rules; no model call','state':state,'quota':q,'latest_evaluation':last.get('record_url') if last else None,'decision':'기존 설정 유지; 다음 고정 평가에서 판단','model_work_gate':q.get('gate','quota_unknown')}
    if state.get('training',{}).get('decisions_per_second',100)<1.74 and state.get('backend')=='3d':out['decision']='2만 행동+평가가 4시간을 넘을 수 있음. 다음 구간 경계에서 2D 병행 조건 확인.'
    atomic(run/'reviews'/f'{time.time_ns()}.json',out);event(run,'review','30분 자동 검토',**out)

def command(run,args,deadline=None):
    log=run/'logs'/f'job-{time.time_ns()}.log';cmd=[str(PYTHON),'-m','lab.learning',*map(str,args)]
    event(run,'command','정해진 실험 구간 실행',command=' '.join(cmd),command_ko='저장된 설정으로 로컬 CPU에서 학습 또는 평가합니다.',log=asset(run,log))
    with log.open('w') as f:
        p=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        atomic(run/'active-job.json',{'pid':p.pid,'command':cmd,'started_at':now(),'log':asset(run,log)})
        stopping=None
        while p.poll() is None:
            atomic(run/'campaign-heartbeat.json',{'pid':os.getpid(),'child':p.pid,'at':now(),'epoch':time.time()})
            if (run/'STOP').exists() or (deadline and time.time()>deadline):
                if stopping is None:p.terminate();stopping=time.time();event(run,'stop','실행 시간 경계에서 안전 저장 요청',pid=p.pid)
                elif time.time()-stopping>180:os.killpg(p.pid,signal.SIGKILL)
            last=read(run/'last-review.json',{'epoch':0})
            if time.time()-last['epoch']>=1800:review(run);atomic(run/'last-review.json',{'epoch':time.time()})
            time.sleep(5)
    if p.returncode!=0:
        event(run,'error','실험 프로세스 오류: 새 코드 수정 필요',exit_code=p.returncode,log=asset(run,log));return False
    return True

def latest_checkpoint(run,trial):
    files=sorted((run/'checkpoints'/trial).glob('step-*.zip'));return files[-1] if files else None

def config_for(run,trial,**patch):
    base=read(run/'configs/3d-food-near-seed11.json');base.update(patch,trial=trial);atomic(run/'configs'/f'{trial}.json',base);return base

def eval_records(run,trial):return [r for p in sorted((run/'evaluations').glob('*.json')) if (r:=read(p,{})).get('trial')==trial and r.get('policy')=='ppo' and not r.get('selection_holdout')]

def obstacle_gate(run,trial):
    rs=eval_records(run,trial);pre=[read(p) for p in (run/'evaluations').glob('*.json') if read(p,{}).get('policy')=='untrained' and read(p,{}).get('trial')==trial]
    return len(rs)>=2 and bool(pre) and all(r['success_rate']>=.7 and r['success_rate']-pre[0]['success_rate']>=.2 for r in rs[-2:])

def run_trial(run,config,workers,limit,deadline,resume_from=None):
    trial=config['trial'];cf=run/'configs'/f'{trial}.json';checkpoint=latest_checkpoint(run,trial) or resume_from
    initial=not latest_checkpoint(run,trial)
    if initial and not checkpoint:
        if not command(run,['train',run,'--config',cf,'--steps',0,'--workers',workers],deadline):return False
        checkpoint=latest_checkpoint(run,trial)
    # Every newly created trial gets a same-condition pre-learning evaluation.
    if not any(read(p,{}).get('trial')==trial and read(p,{}).get('policy')=='untrained' for p in (run/'evaluations').glob('*.json')):
        if not command(run,['evaluate',run,'--config',cf,'--checkpoint',checkpoint,'--policy','untrained','--workers',workers],deadline):return False
    starting=read(str(checkpoint).removesuffix('.zip')+'.json',{}).get('timesteps',0);target=starting+limit if resume_from and initial else limit
    last_eval=time.time();start=time.time()
    while time.time()<deadline and not (run/'STOP').exists():
        checkpoint=latest_checkpoint(run,trial) or checkpoint;steps=read(str(checkpoint).removesuffix('.zip')+'.json',{}).get('timesteps',0)
        if steps>=target:break
        update_state(run,backend=config['backend'],question='먹이까지의 거리가 줄어드는 행동을 보상하면 도달률이 높아질까?',change=f'{trial}: {config["reward_mode"]} 보상, seed {config["seed"]}',next_action='한 시간마다 학습에 쓰지 않은 20개 시작 조건으로 평가')
        if not command(run,['train',run,'--config',cf,'--steps',min(2048,target-steps),'--workers',workers,'--checkpoint',checkpoint,'--deadline',deadline],deadline):return False
        checkpoint=latest_checkpoint(run,trial)
        if time.time()-last_eval>=3000 or read(str(checkpoint).removesuffix('.zip')+'.json',{}).get('timesteps',0)>=target:
            if not command(run,['evaluate',run,'--config',cf,'--checkpoint',checkpoint,'--policy','ppo','--workers',workers],deadline):return False
            last_eval=time.time()
        # Throughput fallback uses sustained training, not the initial short benchmark.
        speed=read(run/'trainer-heartbeat.json',{}).get('decisions_per_second',100)
        if config['backend']=='3d' and time.time()-start>1200 and 20000/max(.01,speed)*1.25>4*3600:
            atomic(run/'fallback-request.json',{'at':now(),'speed':speed,'reason':'sustained 3D rate predicts >4h for 20k + evaluation'});event(run,'decision','지속 처리량에 따라 2D 병행 요청',speed=speed);break
    if checkpoint and time.time()<deadline and (not eval_records(run,trial) or eval_records(run,trial)[-1].get('checkpoint')!=asset(run,checkpoint)):
        command(run,['evaluate',run,'--config',cf,'--checkpoint',checkpoint,'--policy','ppo','--workers',workers],deadline)
    return True

def finalize(run,trials,deadline):
    update_state(run,status='finalizing',activity='선택에 사용하지 않은 조건으로 최종 검증',next_action='실패 장면을 포함해 결과와 회고를 정리')
    for trial in trials:
        checkpoint=latest_checkpoint(run,trial);cf=run/'configs'/f'{trial}.json'
        if checkpoint and time.time()<deadline and not (run/'STOP').exists():
            workers=4 if read(cf)['backend']=='3d' else 1
            command(run,['evaluate',run,'--config',cf,'--checkpoint',checkpoint,'--policy','ppo','--seed-start',90000,'--episodes',30,'--tag','holdout','--workers',workers],deadline)
    from .quota import get_quota
    q=get_quota();base=read(run/'run.json').get('quota_start',{})
    if q.get('status')=='available' and abs(q.get('resets_at',0)-base.get('resets_at',0))<=120:q['increase_pp']=max(0,q['used_percent']-base.get('used_percent',0))
    atomic(run/'quota.json',q)
    from .report import build_report
    build_report(run)
    stopped=(run/'STOP').exists();update_state(run,status='stopped' if stopped else 'completed',ended_at=now(),ended_epoch=time.time(),activity='첫날 회차 종료',result='실제 성과와 미완료 항목은 최종 보고서에서 각각 판정했습니다.',next_action='타임라인과 최종 보고서에서 실패 원인과 다음 실험을 확인');event(run,'finish','첫날 실험 종료',report=asset(run,run/'report.json'));publish(run)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();run=Path(a.run).resolve();cfg=read(run/'run.json');origin=dt.datetime.fromisoformat(cfg['implementation_started_at']).timestamp();base_end=origin+cfg['base_hours']*3600;hard_end=origin+cfg['max_hours']*3600
    with lock(run/'.campaign.lock'):
        atomic(run/'campaign.json',{'pid':os.getpid(),'started_at':now(),'base_end':base_end,'hard_end':hard_end,'model_calls':False})
        caffeine=subprocess.Popen(['caffeinate','-i','-w',str(os.getpid())]);trials=[]
        try:
            baseline=read(run/'baseline-process.json',{})
            while not (run/'baselines.json').exists() and alive(baseline.get('pid')) and time.time()<base_end-3600:
                atomic(run/'campaign-heartbeat.json',{'pid':os.getpid(),'at':now(),'epoch':time.time(),'waiting':'baselines'});time.sleep(5)
            if not (run/'baselines.json').exists():raise RuntimeError('Baseline process ended without completed baseline records; inspect logs/baselines.log')
            primary=read(run/'configs/3d-food-near-seed11.json');trials.append(primary['trial'])
            if not run_trial(run,primary,4,20000,min(base_end-5400,time.time()+3*3600)):raise RuntimeError('Primary trial needs code investigation')
            if read(run/'fallback-request.json'):
                proxy=config_for(run,'2d-food-near-seed11',backend='2d');trials.append(proxy['trial']);run_trial(run,proxy,1,50000,min(base_end-5400,time.time()+3600))
                # Transfer is a separate 3D evaluation; never mixed into 2D success.
                cp=latest_checkpoint(run,proxy['trial'])
                if cp:command(run,['evaluate',run,'--config',run/'configs'/f'{primary["trial"]}.json','--checkpoint',cp,'--policy','2d-to-3d-transfer','--workers',4],base_end-3600)
            replicate=config_for(run,'3d-food-near-seed29',seed=29);trials.append(replicate['trial']);run_trial(run,replicate,4,20000,min(base_end-5400,time.time()+2.5*3600))
            # One-factor reward ablation, same seed and environment. Capped if late.
            if time.time()<base_end-3*3600 and read(run/'quota.json',{}).get('gate')=='continue':
                ablation=config_for(run,'3d-food-near-sparse-seed11',reward_mode='sparse');trials.append(ablation['trial']);run_trial(run,ablation,4,12000,base_end-5400)
            # Extend only for a justified new task after the predeclared success gate.
            if obstacle_gate(run,primary['trial']) and not (run/'STOP').exists() and read(run/'quota.json',{}).get('gate')=='continue':
                obstacle=config_for(run,'3d-obstacles-near-seed11',task='obstacles');trials.append(obstacle['trial']);event(run,'decision','고정 평가 기준 충족: 장애물 과제로 확장',gate='>=70% twice and +20pp above untrained');run_trial(run,obstacle,4,12000,min(hard_end-5400,base_end+3600),latest_checkpoint(run,primary['trial']));base_end=min(hard_end,base_end+2*3600)
            elif time.time()<base_end-5400 and read(run/'quota.json',{}).get('gate')=='continue':
                # Generalization is a separate evaluation condition, not concatenated scores.
                wide=config_for(run,'3d-food-wide-seed11',curriculum='wide');trials.append(wide['trial']);run_trial(run,wide,4,12000,base_end-5400,latest_checkpoint(run,primary['trial']))
            # If fixed work finishes early, retain hourly evaluations without burning tokens.
            while time.time()<base_end-5400 and not (run/'STOP').exists():
                last=read(run/'last-review.json',{'epoch':0})
                if time.time()-last['epoch']>=1800:review(run);atomic(run/'last-review.json',{'epoch':time.time()})
                time.sleep(30)
            finalize(run,trials,min(hard_end,base_end))
        except Exception as exc:
            event(run,'error','실험 자동 진행 보류',detail=repr(exc),traceback=traceback.format_exc());update_state(run,status='blocked',activity='코드 확인 필요 · 기록은 계속',result=str(exc),next_action='원본 오류 로그를 확인한 뒤 재개');publish(run)
        finally:
            caffeine.terminate()
if __name__=='__main__':main()
