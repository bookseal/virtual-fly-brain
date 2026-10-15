"""Bounded day-two comparison. Explicit local rules, no background model calls."""
import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path
from .store import *
from .campaign import latest_checkpoint
PYTHON=ROOT/'.venv/bin/python'

def execute(run,module,args,deadline):
    command=[str(PYTHON),'-m',module,*map(str,args)]
    log=run/'logs'/f'job-v2-{time.time_ns()}.log'
    event(run,'command','검증한 비교 실험 실행',command=' '.join(command),command_ko='저장된 조건으로 실행하며, 평가에서는 정책을 바꾸지 않습니다.',log=asset(run,log))
    with log.open('w') as f:
        p=subprocess.Popen(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        atomic(run/'active-job.json',{'pid':p.pid,'command':command,'started_at':now(),'log':asset(run,log)})
        stop_at=None
        while p.poll() is None:
            atomic(run/'campaign-heartbeat.json',{'pid':os.getpid(),'child':p.pid,'at':now(),'epoch':time.time()})
            if time.time()>=deadline or (run/'STOP').exists():
                if stop_at is None:
                    p.terminate();stop_at=time.time();event(run,'stop','시간 경계에서 저장 후 중단 요청')
                elif time.time()-stop_at>120:
                    try:os.killpg(p.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
            time.sleep(3)
    if stop_at:
        event(run,'boundary','계획된 시간 경계에서 작업 종료',returncode=p.returncode);return False
    if p.returncode:
        event(run,'error','실험 실행 오류 · 코드 검토 필요',returncode=p.returncode,log=asset(run,log));raise RuntimeError(f'{module} failed; inspect {log.name}')
    return True

def evaluations(run,c,policy=None,holdout=False):
    return [d for p in sorted((run/'evaluations').glob('*.json')) if (d:=read(p,{})).get('trial')==c['trial'] and (policy is None or d.get('policy')==policy) and bool(d.get('selection_holdout'))==holdout]

def assess(run,c,policy,cp,deadline,holdout=False):
    if time.time()>deadline-120 or (run/'STOP').exists():return False
    args=['evaluate',run,'--config',run/'configs'/f'{c["trial"]}.json','--policy',policy,'--workers','2']
    if cp:args+=['--checkpoint',cp]
    if holdout:args+=['--seed-start','91000','--episodes','30','--tag','holdout']
    return execute(run,'lab.learning',args,deadline)

def prepare(run,c,deadline):
    cp=latest_checkpoint(run,c['trial'])
    if not cp:
        if c['initialization']=='behavior-cloning-from-rule':
            while not (run/'demonstrations/manifest.json').exists():
                if time.time()>deadline-600 or (run/'STOP').exists():return False
                atomic(run/'campaign-heartbeat.json',{'pid':os.getpid(),'at':now(),'epoch':time.time(),'phase':'waiting for demonstrations'})
                time.sleep(5)
            if not execute(run,'lab.imitation',['clone',run,'--config',run/'configs'/f'{c["trial"]}.json'],deadline):return False
        elif not execute(run,'lab.learning',['train',run,'--config',run/'configs'/f'{c["trial"]}.json','--workers','2','--steps','0'],deadline):return False
        cp=latest_checkpoint(run,c['trial'])
    policy='bc-initial' if c['initialization']=='behavior-cloning-from-rule' else 'untrained'
    if not evaluations(run,c,policy):return assess(run,c,policy,cp,deadline)
    return True

def train_to(run,c,target,deadline):
    cp=latest_checkpoint(run,c['trial']);policy='bc-ppo' if c['initialization']=='behavior-cloning-from-rule' else 'ppo'
    while time.time()<deadline-120 and not (run/'STOP').exists():
        if read(run/'quota.json',{}).get('gate') in ['stop_new_model_work','budget_reached','quota_unknown']:return False
        steps=read(str(cp).removesuffix('.zip')+'.json',{}).get('timesteps',0)
        if steps>=target:break
        update_state(run,question='같은 학습량에서 두 경로의 먹이 도달률은 어떻게 달라질까?',change=f'{c["trial"]}: 정규화한 행동, dense 보상',next_action=f'{target:,} 행동 경계와 주기적 고정 평가에서 비교',model_note='로컬 프로그램이 승인된 비교 순서를 실행합니다. GPT의 해석은 연구자의 선택에 별도로 기록합니다.')
        if not execute(run,'lab.learning',['train',run,'--config',run/'configs'/f'{c["trial"]}.json','--workers','2','--steps',min(2048,target-steps),'--checkpoint',cp,'--deadline',deadline],deadline):return False
        cp=latest_checkpoint(run,c['trial']);after=read(str(cp).removesuffix('.zip')+'.json')['timesteps']
        speed=read(run/'trainer-heartbeat.json',{}).get('decisions_per_second',100)
        if c['backend']=='3d' and after>=2048 and 20000/max(.01,speed)*1.25>4*3600 and not (run/'proxy-request.json').exists():
            atomic(run/'proxy-request.json',{'at':now(),'measured_decisions_per_second':speed,'status':'started'})
            proxy={**c,'trial':'2d-diagnostic-seed11','backend':'2d','initialization':'random'};atomic(run/'configs'/f'{proxy["trial"]}.json',proxy)
            event(run,'decision','지속 처리량 기준에 따라 2D 진단을 병행',detail='2D 결과는 별도 표시하며 실제 3D 개선으로 계산하지 않습니다.',speed=speed)
            limit=min(deadline,time.time()+900)
            if execute(run,'lab.learning',['train',run,'--config',run/'configs'/f'{proxy["trial"]}.json','--workers','1','--steps','20000','--deadline',limit],limit):
                proxy_cp=latest_checkpoint(run,proxy['trial']);assess(run,proxy,'ppo',proxy_cp,limit)
                # Same input/output concepts; transfer remains a separately labelled 3D test.
                assess(run,c,'2d-to-3d-transfer',proxy_cp,min(deadline,time.time()+1800))
                atomic(run/'proxy-request.json',{'at':now(),'status':'completed','config':proxy,'checkpoint':str(proxy_cp)})
        last=evaluations(run,c,policy)
        if after>=target or not last or time.time()-__import__('datetime').datetime.fromisoformat(last[-1]['evaluated_at']).timestamp()>3600:
            if not assess(run,c,policy,cp,deadline):return False
    return True

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();run=Path(a.run).resolve();cfg=read(run/'run.json');origin=cfg['started_epoch'];deadline=origin+24*3600;train_end=origin+21*3600
    with lock(run/'.campaign-v2.lock'):
        atomic(run/'campaign-v2.json',{'pid':os.getpid(),'started_at':now(),'hard_end':deadline,'model_calls':False})
        caffeine=subprocess.Popen(['caffeinate','-i','-w',str(os.getpid())])
        try:
            configs=[read(run/'configs'/f'3d-near-{route}-seed{seed}.json') for seed in (11,29,47) for route in ('ppo','bc-ppo')]
            for policy in ('rule','random'):
                if not evaluations(run,configs[0],policy):
                    if not assess(run,configs[0],policy,None,train_end):break
            for c in configs:
                if not prepare(run,c,train_end):break
                if not train_to(run,c,10240,train_end):break
            # Matched online budgets; never extend only the winning route.
            if time.time()<origin+17*3600:
                for c in configs:
                    if not latest_checkpoint(run,c['trial']):break
                    if not train_to(run,c,20480,train_end):break
            # An obstacle extension requires repeated improvement against this route's initial policy.
            for c in configs:
                if time.time()>origin+18*3600:break
                policy='bc-ppo' if c['initialization']=='behavior-cloning-from-rule' else 'ppo'
                rows=evaluations(run,c,policy);initial=evaluations(run,c,'bc-initial' if policy=='bc-ppo' else 'untrained')
                if len(rows)>=2 and initial and all(r['success_rate']>=.7 and r['success_rate']-initial[0]['success_rate']>=.2 for r in rows[-2:]) and read(run/'quota.json',{}).get('gate')=='continue':
                    ob={**c,'trial':c['trial']+'-obstacles','task':'obstacles','initialization':'transfer'};atomic(run/'configs'/f'{ob["trial"]}.json',ob)
                    # Persist the parent weights with an explicit transfer label.
                    if not execute(run,'lab.learning',['train',run,'--config',run/'configs'/f'{ob["trial"]}.json','--workers','2','--steps','0','--checkpoint',latest_checkpoint(run,c['trial'])],train_end):break
                    cp=latest_checkpoint(run,ob['trial']);assess(run,ob,'transfer-initial',cp,train_end)
                    before=read(str(cp).removesuffix('.zip')+'.json')['timesteps'];train_to(run,ob,before+10240,train_end);configs.append(ob)
                    event(run,'decision','장애물 확장 기준 충족',parent=c['trial'],rule='>=70% twice and >=20pp above route initialization');break
            update_state(run,status='finalizing',activity='선택에 쓰지 않은 30개 조건 최종 평가',next_action='모든 경로의 실제 결과와 실패를 비교')
            for c in configs:
                cp=latest_checkpoint(run,c['trial'])
                if cp and not evaluations(run,c,holdout=True):assess(run,c,'bc-ppo' if c['initialization']=='behavior-cloning-from-rule' else 'ppo',cp,deadline-600,True)
            from .report import build_report
            build_report(run)
            update_state(run,status='stopped' if (run/'STOP').exists() else 'completed',activity='비교 회차 종료 · 기록과 회고 정리',ended_epoch=time.time(),ended_at=now(),result='실제로 완료한 경로와 새 조건 결과를 장부에서 확인할 수 있습니다. 시간·사용량으로 생략한 경로는 성공으로 계산하지 않습니다.',next_action='전체 회고와 재현 자료 확인');event(run,'finish','24시간 상한 내 비교 회차 종료');publish(run)
        except Exception as exc:
            update_state(run,status='blocked',activity='코드 검토 필요 · 기록과 공개는 계속',result=str(exc),next_action='실패 로그 확인 후 재개');event(run,'error','자동 실험 진행 보류',detail=repr(exc));publish(run)
        finally:caffeine.terminate()
if __name__=='__main__':main()
