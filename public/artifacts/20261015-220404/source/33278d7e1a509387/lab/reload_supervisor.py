"""Load verified supervisor code at a child-job boundary without interrupting it."""
import argparse,os,signal,subprocess,time
from pathlib import Path
from .store import *
from .manage import matching,launch

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();run=Path(a.run).resolve()
    with lock(run/'.supervisor-reload.lock'):
        parent=read(run/'campaign-v2.json',{}).get('pid');child=read(run/'active-job.json',{}).get('pid')
        if not matching(parent,'lab.campaign_v2',run):raise RuntimeError('Supervisor identity changed')
        # The child has its own process group and completes the already started job.
        os.kill(parent,signal.SIGTERM)
        event(run,'maintenance','진행 중인 평가·학습 경계에서 감독 코드 갱신',detail='현재 자식 작업을 중단하지 않습니다. 작업 종료 후 새 감독 프로세스가 완료된 결과부터 이어갑니다.')
        caffeine=subprocess.Popen(['caffeinate','-i','-w',str(os.getpid())])
        try:
            deadline=read(run/'run.json')['started_epoch']+24*3600
            while time.time()<deadline:
                live=any(matching(child,m,run) for m in ('lab.learning','lab.imitation'))
                if not live:break
                time.sleep(5)
            else:raise RuntimeError('Child still active at campaign deadline')
            print('new supervisor',launch(run,'lab.campaign_v2','campaign-v2.json'),flush=True)
        finally:caffeine.terminate()
if __name__=='__main__':main()
