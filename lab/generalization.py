"""Bounded supplementary evaluation, isolated from the primary training state."""
import argparse,os,signal,subprocess,time
from pathlib import Path
from .store import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();run=Path(a.run).resolve()
    with lock(run/'.generalization.lock'):
        trial='3d-wide-generalization-seed11';config=read(run/'configs/3d-near-bc-ppo-seed11.json')
        config.update(trial=trial,curriculum='wide',purpose='supplementary generalization diagnosis; not the final holdout')
        path=run/'configs'/f'{trial}.json';atomic(path,config)
        checkpoint=run/'checkpoints/3d-near-bc-ppo-seed11/step-000010240.zip'
        end=min(time.time()+5400,read(run/'run.json')['started_epoch']+24*3600)
        atomic(run/'generalization.json',{'status':'running','at':now(),'pid':os.getpid(),'seed_start':30000,'episodes':20,'note':'거리와 방향을 넓힌 별도 진단. 가까운 먹이 점수 및 최종 91000번대 평가와 분리합니다.'})
        for policy,cp in [('rule',None),('bc-transfer-diagnostic',checkpoint)]:
            if any(read(p).get('trial')==trial and read(p).get('policy')==policy for p in (run/'evaluations').glob('*.json')):continue
            if time.time()>=end or (run/'STOP').exists():break
            cmd=[str(ROOT/'.venv/bin/python'),'-m','lab.learning','evaluate',str(run),'--config',str(path),'--policy',policy,'--workers','2','--seed-start','30000','--episodes','20','--tag','diagnostic','--background-evaluation']
            if cp:cmd+=['--checkpoint',str(cp)]
            event(run,'command','더 넓은 먹이 위치에서 별도 진단',command=' '.join(cmd),command_ko='주 학습은 유지하고 두 worker로 넓은 위치의 20개 조건을 평가합니다. 모델을 업데이트하지 않습니다.')
            log=run/'logs'/f'generalization-{policy}.log'
            with log.open('a') as f:
                process=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
                try:code=process.wait(timeout=max(1,end-time.time()))
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:process.wait(timeout=30)
                    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
                    code=-1
            if code:
                atomic(run/'generalization.json',{'status':'failed','at':now(),'policy':policy,'log':asset(run,log)});event(run,'error','별도 일반화 진단 보류',policy=policy,log=asset(run,log));return
        atomic(run/'generalization.json',{'status':'completed' if time.time()<end else 'time_limit','at':now(),'trial':trial});publish(run)
if __name__=='__main__':main()
