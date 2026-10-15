"""Serial public snapshots from a dedicated checkout; never stage live code."""
import argparse,importlib.util,subprocess,tempfile,shutil,os,time,urllib.request,json
from pathlib import Path
from .store import ROOT,RUNS,read,atomic,lock,event,publish,now

def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*map(str,args)],cwd=cwd,stderr=subprocess.STDOUT,text=True).strip()

def publish_once(run):
    spec=importlib.util.spec_from_file_location('public_export',ROOT/'scripts/export_public.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
    checkout=RUNS/'publisher-checkout'
    with lock(ROOT/'.git/fly-publish.lock'):
        git('fetch','origin','main')
        if not checkout.exists():git('worktree','add','--detach',checkout,'origin/main')
        if git('status','--porcelain',cwd=checkout):raise RuntimeError('Publisher checkout has unexpected changes; preserving them')
        # Only advance this dedicated detached checkout. No user working tree changes.
        ahead=git('rev-list','--count','origin/main..HEAD',cwd=checkout)
        if ahead!='0':
            git('rebase','origin/main',cwd=checkout)
            git('push','origin','HEAD:main',cwd=checkout)
        git('checkout','--detach','origin/main',cwd=checkout)
        with tempfile.TemporaryDirectory(prefix='snapshot-',dir=RUNS) as tmp:
            out=Path(tmp)/'public';shutil.copytree(checkout/'public',out)
            dest=out/'artifacts'/run.name
            if dest.exists():shutil.rmtree(dest)
            manifest=ex.export_run(run,out);ex.audit(out)
            # Commit only validated data. Retain old public run directories.
            old=Path(tmp)/'previous';os.replace(checkout/'public',old);os.replace(out,checkout/'public')
        git('add','--','public',cwd=checkout)
        if not git('diff','--cached','--name-only',cwd=checkout):return {'status':'unchanged','at':now()}
        git('commit','-m',f'Record {run.name}: {len(manifest["intervals"])} intervals',cwd=checkout)
        sha=git('rev-parse','HEAD',cwd=checkout);git('push','origin','HEAD:main',cwd=checkout)
        state={'status':'pushed','at':now(),'commit':sha,'commit_url':f'https://github.com/bookseal/virtual-fly-brain/commit/{sha}','snapshot_at':manifest['publication']['exported_at'],'url':'https://bookseal.github.io/virtual-fly-brain/'}
        atomic(run/'deployment.json',state);publish(run)
    # Observe the public artifact, not merely git push success.
    deadline=time.time()+600
    url=f'https://bookseal.github.io/virtual-fly-brain/artifacts/{run.name}/manifest.json'
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(url+'?verify='+str(time.time_ns()),timeout=20) as response:remote=json.load(response)
            if remote.get('publication',{}).get('exported_at','')>=manifest['publication']['exported_at']:
                state.update(status='deployed',verified_at=now());break
        except (OSError,ValueError):pass
        time.sleep(15)
    else:state.update(status='deployment_pending',reason='Push completed; public snapshot not yet verified')
    atomic(run/'deployment.json',state);event(run,'publication','공개 스냅샷 배포 확인',**state);publish(run)
    return state

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('--once',action='store_true');ap.add_argument('--interval',type=int,default=1800);a=ap.parse_args();run=Path(a.run).resolve()
    with lock(run/'.publisher.lock'):
        atomic(run/'publisher.json',{'pid':os.getpid(),'at':now()})
        while True:
            try:print(json.dumps(publish_once(run),ensure_ascii=False),flush=True)
            except Exception as exc:
                atomic(run/'deployment.json',{'status':'failed','at':now(),'reason':str(exc)[-600:]});event(run,'error','공개 배포 보류 · 로컬 기록 유지',detail=str(exc)[-600:]);publish(run)
            if a.once:break
            if read(run/'state.json',{}).get('status') in ['completed','failed','stopped'] and (run/'final-recorded.json').exists():
                if read(run/'retrospective.json',{}).get('status') in ['done','failed','omitted']:break
            if time.time()>read(run/'run.json')['started_epoch']+25*3600:break
            time.sleep(a.interval)
if __name__=='__main__':main()
