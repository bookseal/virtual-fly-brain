"""Scoped process management. Never terminates another service or reused PID."""
import argparse,os,subprocess,sys,time,urllib.request
from pathlib import Path
from .store import *

def matching(pid,module,run):
    if not pid:return False
    p=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
    return p.returncode==0 and f'-m {module} ' in p.stdout and str(run) in p.stdout

def launch(run,module,marker,python=None,extra=()):
    existing=read(run/marker,{})
    if matching(existing.get('pid'),module,run):return existing['pid']
    p=subprocess.Popen([str(python or ROOT/'.venv/bin/python'),'-m',module,str(run),*extra],cwd=ROOT,stdout=(run/'logs'/f'{module.split(".")[-1]}-managed.log').open('a'),stderr=subprocess.STDOUT,start_new_session=True)
    atomic(run/marker,{'pid':p.pid,'at':now()});return p.pid

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['start','status','stop','retry-videos']);ap.add_argument('run');ap.add_argument('--resume',action='store_true');a=ap.parse_args();run=Path(a.run).resolve()
    if not (run/'run.json').exists():raise SystemExit('Existing run.json required; no implicit new campaign')
    if a.action=='stop':(run/'STOP').touch();event(run,'stop','사용자가 관리 명령으로 안전 중단 요청');return
    if a.action=='retry-videos':
        for p in list((run/'intervals').glob('*.json'))+list((run/'summaries').glob('*.json')):
            with lock(run/'.snapshot.lock'):
                r=read(p)
                if r.get('render',{}).get('status')=='failed':r['render']={'status':'queued','previous_failure':r['render']};atomic(p,r)
        publish(run);launch(run,'lab.video','video-worker.json');return
    if a.action=='start':
        if (run/'STOP').exists():
            if not a.resume:raise SystemExit('Run was stopped. Use --resume to explicitly resume.')
            (run/'STOP').unlink();event(run,'resume','사용자가 관리 명령으로 재개 요청')
        try:
            with urllib.request.urlopen('http://127.0.0.1:8766/',timeout=2) as r:
                if b'Fly Brain Lab' not in r.read():raise SystemExit('8766 belongs to another service; leave it running')
        except OSError:
            subprocess.Popen([sys.executable,'-m','http.server','8766','--bind','127.0.0.1','--directory',str(ROOT/'site')],stdout=(run/'logs/server-managed.log').open('a'),stderr=subprocess.STDOUT,start_new_session=True)
        if not (run/'baselines.json').exists():launch(run,'lab.baselines','baseline-process.json',extra=('--workers','4'))
        launch(run,'lab.recorder','recorder.json');launch(run,'lab.video','video-worker.json');launch(run,'lab.campaign','campaign.json')
    result={'run':run.name,'state':read(run/'state.json',{}),'quota':read(run/'quota.json',{}),'processes':{m:matching(read(run/f,{}).get('pid'),m,run) for m,f in [('lab.recorder','recorder.json'),('lab.video','video-worker.json'),('lab.campaign','campaign.json'),('lab.baselines','baseline-process.json')]},'recorded_intervals':len(list((run/'intervals').glob('*.json'))),'url':'http://127.0.0.1:8766/#experiments'}
    print(__import__('json').dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
