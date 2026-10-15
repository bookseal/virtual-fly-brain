import argparse,os,signal,time
from pathlib import Path
from .store import *
from .quota import get_quota

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('--interval',type=float,default=600);ap.add_argument('--no-quota',action='store_true');a=ap.parse_args();run=Path(a.run).resolve()
    cfg=read(run/'run.json');stop=False
    def stopping(*_):
        nonlocal stop;stop=True
    signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
    with lock(run/'.recorder.lock'):
        atomic(run/'recorder.json',{'pid':os.getpid(),'started_at':now()});last_quota=0
        while not stop:
            elapsed=time.time()-cfg['started_epoch'];index=int(elapsed//a.interval)
            for n in range(index+1):
                if not (run/'intervals'/f'{n:04d}.json').exists():snapshot(run,n,a.interval)
            if not a.no_quota and time.time()-last_quota>=1800:
                q=get_quota();last_quota=time.time();base=cfg.get('quota_start',{})
                if q['status']=='available' and base.get('status')=='available':
                    same=abs(q['resets_at']-base['resets_at'])<=120
                    q['increase_pp']=max(0,q['used_percent']-base['used_percent']) if same else None
                    q['gate']='stop_new_model_work' if not same or q['increase_pp']>=60 else 'continue'
                    if same and q['increase_pp']>=70:q['gate']='budget_reached'
                else:q['gate']='quota_unknown'
                atomic(run/'quota.json',q);event(run,'quota','사용량 확인',quota=q);publish(run)
            atomic(run/'recorder-heartbeat.json',{'pid':os.getpid(),'at':now(),'epoch':time.time()})
            state=read(run/'state.json',{})
            if state.get('status') in ['completed','stopped','failed']:
                # Capture a terminal record even between ten-minute ticks.
                if not (run/'final-recorded.json').exists():
                    snapshot(run,index+1,a.interval,terminal=True);atomic(run/'final-recorded.json',{'at':now()})
                break
            if elapsed>cfg.get('max_hours',12)*3600+600:
                event(run,'error','기록기 최대 실행 시간 도달');break
            time.sleep(min(5,a.interval))
if __name__=='__main__':main()
