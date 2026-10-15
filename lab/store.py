from __future__ import annotations
import contextlib, datetime as dt, fcntl, html, json, os, tempfile, time, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs'
def now(): return dt.datetime.now().astimezone().isoformat(timespec='seconds')
def read(path, default=None):
    try: return json.loads(Path(path).read_text())
    except (OSError, ValueError): return default
@contextlib.contextmanager
def lock(path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN)
def atomic(path, data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def event(run, kind, title, **data):
    run=Path(run);run.mkdir(parents=True,exist_ok=True)
    e={'id':uuid.uuid4().hex,'at':now(),'epoch':time.time(),'actor':'local-script','kind':kind,'title':title,**data}
    with lock(run/'.events.lock'):
        with (run/'events.jsonl').open('a') as f:
            f.write(json.dumps(e,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
    return e

def events(run):
    out=[]
    try:
        for line in (Path(run)/'events.jsonl').read_text().splitlines():
            try:out.append(json.loads(line))
            except ValueError:pass
    except OSError:pass
    return out

def update_state(run, **patch):
    run=Path(run)
    with lock(run/'.state.lock'):
        s=read(run/'state.json',{});s.update(patch);s['updated_at']=now();atomic(run/'state.json',s)
    return s

def asset(run,path):
    return 'artifacts/'+Path(run).name+'/'+str(Path(path).relative_to(run))

def publish(run):
    with lock(Path(run)/'.publish.lock'):
        run=Path(run);config=read(run/'run.json',{});state=read(run/'state.json',{})
        snaps=[read(p,{}) for p in sorted((run/'intervals').glob('*.json'))]
        evals=[read(p,{}) for p in sorted((run/'evaluations').glob('*.json'))]
        manifest={'schema_version':1,'run':config,'state':state,'intervals':snaps,'evaluations':evals,'quota':read(run/'quota.json',{}),'recorder_heartbeat':read(run/'recorder-heartbeat.json',{}),'summaries':[read(p,{}) for p in sorted((run/'summaries').glob('*.json'))],'retrospective':read(run/'retrospective.json',{}),'report':asset(run,run/'report.html') if (run/'report.html').exists() else None,'updated_at':now()}
        for name in ('journal','research','diagnostics','deployment','analysis','policy-audit','generalization','noise-ablation','compatibility'):
            manifest[name]=read(run/(name+'.json'),{})
        atomic(run/'manifest.json',manifest)
        dest=ROOT/'site/experiments/index.json'
        with lock(ROOT/'site/experiments/.index.lock'):
            idx=read(dest,{'runs':[]});entry={'run_id':run.name,'started_at':config.get('started_at'),'manifest':asset(run,run/'manifest.json')}
            idx['runs']=[entry]+[r for r in idx['runs'] if r['run_id']!=run.name]
            idx['runs'].sort(key=lambda r:r.get('started_at',''),reverse=True)
            idx['updated_at']=now();atomic(dest,idx)

def evidence_svg(run,interval):
    """A factual status card, never a synthetic animal rollout."""
    path=Path(run)/'media'/f"interval-{interval['index']:04d}.svg";path.parent.mkdir(exist_ok=True)
    def safe(s):return html.escape(str(s))
    lines=[f"{interval['elapsed_minutes']:.0f}분 · {interval.get('backend','setup')}",interval['title'],interval['question'],interval['result'],interval['next_action']]
    # Browser wraps explanatory HTML; SVG card deliberately contains only short factual lines.
    rows=''.join(f'<text x="52" y="{150+i*62}" font-size="{26 if i==1 else 20}" fill="{("#22313e" if i==1 else "#657586")}">{safe(t[:64])}</text>' for i,t in enumerate(lines))
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#f7f8fa"/><rect x="25" y="25" width="1230" height="670" rx="20" fill="white" stroke="#dde4eb"/><text x="52" y="82" fill="#cd5433" font-size="20" font-family="sans-serif">FLY BRAIN LAB / 실제 진행 기록</text><g font-family="Apple SD Gothic Neo,sans-serif">{rows}<text x="52" y="590" font-size="16" fill="#687480">{safe(interval["recorded_at"])}</text><text x="52" y="625" font-size="16" fill="#687480">행동 영상이 아닌 상태 카드 · 수치는 확보된 기록만 표시</text></g></svg>')
    return asset(run,path)

def snapshot(run,index,interval_seconds=600,terminal=False):
    run=Path(run);path=run/'intervals'/f'{index:04d}.json'
    with lock(run/'.snapshot.lock'):
        if path.exists():return read(path)
        cfg=read(run/'run.json',{});state=read(run/'state.json',{});all_events=events(run)
        end=time.time();scheduled=cfg.get('started_epoch',end)+index*interval_seconds;start=cfg.get('started_epoch',end)+(index-1)*interval_seconds
        delayed=end-scheduled>max(30,interval_seconds) and not terminal
        boundary=end if terminal or index==0 else min(end,scheduled+5)
        recent=[e for e in all_events if start < e['epoch'] <= boundary]
        last=recent[-1] if recent else {}
        evaluation=read(run/'latest-evaluation.json',{})
        row={'id':f'{run.name}-{index:04d}','index':index,'recorded_at':now(),'scheduled_epoch':cfg.get('started_epoch',end)+index*interval_seconds,'elapsed_minutes':(end-cfg.get('started_epoch',end))/60,'backend':state.get('backend','setup'),'status':state.get('status','preparing'),'title':last.get('title',state.get('activity','진행 상태 확인')),'question':state.get('question','가상 초파리 실험을 재현 가능하게 실행할 수 있을까?'),'change':state.get('change','실행 환경과 기록 시스템 준비'),'result':state.get('result','아직 행동 평가 결과가 없습니다.'),'next_action':state.get('next_action','설치 후 실제 몸을 실행하고 속도를 측정합니다.'),'training':state.get('training',{}),'events':recent,'evaluation':evaluation or None,'media':[],'render':{'status':'queued'},'actor':'local-script'}
        row['record_type']='end' if terminal else ('start' if index==0 else 'interval')
        if terminal:row['scheduled_epoch']=end
        row['recording_delay_seconds']=max(0,end-scheduled)
        if delayed:
            row.update(status='gap',title='기록기 중단 구간 · 원본 사건만 복구',question='이 시각에 기록기가 응답했는가?',change='예약 시각에 기록을 저장하지 못했습니다.',result='이전 상태를 현재 상태로 추정하지 않았습니다. 원본 사건 시각을 확인하세요.',next_action='복구 후 다음 구간부터 실시간 기록을 이어갑니다.',evaluation=None,training={})
        row['media']=[evidence_svg(run,row)]
        if evaluation:row['last_evaluated_at']=evaluation.get('evaluated_at')
        atomic(path,row)
    publish(run);return row

def preserve_source(run):
    import hashlib,shutil
    run=Path(run);files=list((ROOT/'lab').glob('*.py'))+[ROOT/'requirements.lock.txt',ROOT/'video/package-lock.json']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.exists()}
    key=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16];dest=run/'source'/key
    if not dest.exists():
        dest.mkdir(parents=True)
        for name in hashes:
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(ROOT/name,target)
        atomic(dest/'sha256.json',hashes)
    result={'at':now(),'version':key,'path':asset(run,dest),'sha256':hashes};atomic(run/'source-version.json',result);return result
