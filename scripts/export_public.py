"""Create a portable, privacy-filtered snapshot without modifying local records.

Only referenced files are copied; credentials, account usage, process state and
machine paths are excluded. Original full episode data stays in evaluation JSON.
"""
import argparse,copy,datetime as dt,html,json,re,shutil,sys,time,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PRIVATE_KEYS={'quota','quota_start','quota_latest','pid','child','resets_at','used_percent','increase_pp','budget_pp','expand_stop_pp','recorder_heartbeat','source_version','probe','log','traceback','command_ko_private'}
LOCAL_NAMES=[]
if (ROOT/'HANDOFF.md').exists():LOCAL_NAMES=re.findall(r'사용자\([^,]+,\s*([^)]+)\)',(ROOT/'HANDOFF.md').read_text())
PRIVATE_TEXT=re.compile(r'구독|주간.{0,20}(한도|사용)|시작 시 주간|account/rateLimits|used_percent|resets_at')
SECRET=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
def read(p):return json.loads(Path(p).read_text())
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k not in PRIVATE_KEYS and not k.startswith('quota_')}
    if isinstance(value,list):return [clean(v) for v in value if not isinstance(v,dict) or v.get('kind')!='quota']
    if not isinstance(value,str):return value
    value=value.replace(str(ROOT)+'/', '').replace(str(ROOT),'.')
    value=re.sub(r'/Users/[^/\s"<>]+','/Users/USER',value)
    value=re.sub(r'사용자\([^)]*\)','로컬 사용자',value)
    for name in LOCAL_NAMES:value=value.replace(name,'사용자')
    if PRIVATE_TEXT.search(value):return '로컬 실행 준비 기록. 개인 계정 사용량은 공개본에서 제외했습니다.'
    if SECRET.search(value):raise ValueError('Credential-shaped text in public export')
    return value
def brief(e):return {k:v for k,v in e.items() if k!='episodes_raw'} if e else e
def public_report(dest,report):
    esc=lambda v:html.escape(str(v));labels={'record_system':'10분 시각 기록','3d_execution':'실제 3D 몸 실행','learning_improvement':'정책의 학습 개선','obstacles':'장애물 회피'}
    body=f'<h1>실험 결과 · 공개 기록</h1><p>생성 시각 {esc(report.get("generated_at",""))}. 공개 시점의 관측 결과입니다.</p>'
    for k,v in report.get('verdict',{}).items():body+=f'<section><h2>{esc(labels.get(k,k))} · {esc(v.get("status"))}</h2><pre>{esc(json.dumps(v,ensure_ascii=False,indent=2))}</pre></section>'
    body+='<p><a href="report.json">보고서 JSON</a> · <a href="../../#experiments">실험 타임라인으로</a></p>'
    (dest/'report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fly Brain Lab 공개 보고서</title><style>body{font:16px/1.7 system-ui;max-width:1000px;margin:32px auto;padding:20px;background:#f7f8fa;color:#22313e}section{padding:18px;background:white;border:1px solid #ddd;border-radius:12px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}</style>'+body+'</html>')
def export_run(run,output):
    run=run.resolve();dest=output/'artifacts'/run.name;dest.mkdir(parents=True,exist_ok=True)
    with (run/'manifest.json').open() as f:original=json.load(f)
    exported_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds');m=clean(copy.deepcopy(original))
    m['run']['public_url']='https://bookseal.github.io/virtual-fly-brain/'
    m['publication']={'mode':'snapshot','exported_at':exported_at,'snapshot_epoch':time.time(),'repository':'https://github.com/bookseal/virtual-fly-brain','note':'로컬에서 실행한 실험 결과의 공개 스냅샷입니다.'}
    references=set()
    def visit(v):
        if isinstance(v,dict):
            for a in v.values():visit(a)
        elif isinstance(v,list):
            for a in v:visit(a)
        elif isinstance(v,str) and v.startswith('artifacts/'+run.name+'/'):references.add(v)
    for group in ('intervals','summaries'):
        for row in m.get(group,[]):
            original_row=next((r for r in original.get(group,[]) if r.get('id')==row.get('id')),None)
            if original_row and PRIVATE_TEXT.search(str(original_row.get('result',''))):
                row['render']={'status':'omitted','reason':'개인 계정 사용량을 담은 준비 영상은 공개하지 않습니다.'}
            row.pop('correction',None)
            row.get('render',{}).pop('composition',None)
            row['evaluation']=brief(row.get('evaluation'))
            visit(row)
            rel=('intervals/'+f'{row["index"]:04d}.json') if group=='intervals' else ('summaries/'+f'hour-{row["index"]:02d}.json')
            write(dest/rel,row)
    for e in m.get('evaluations',[]):visit(e)
    for p in sorted((run/'evaluations').glob('*.json')):
        e=clean(read(p));write(dest/'evaluations'/p.name,e);visit(e)
    m['evaluations']=[brief(e) for e in m.get('evaluations',[])]
    visit(m.get('retrospective',{}));visit(m.get('state',{}))
    if (run/'report.json').exists():visit(clean(read(run/'report.json')))
    for ref in sorted(references):
        rel=Path(ref).relative_to(Path('artifacts')/run.name)
        if '..' in rel.parts:raise ValueError('Path escapes run')
        src=run/rel;target=dest/rel
        if not src.is_file() or target.exists():continue
        if src.suffix not in {'.mp4','.png','.svg','.json','.zip','.pkl'}:continue
        target.parent.mkdir(parents=True,exist_ok=True)
        if src.suffix=='.json':write(target,clean(read(src)))
        elif src.suffix=='.svg':
            svg=src.read_text();svg=re.sub(r'(?<=>)[^<>]*(?=<)',lambda m:clean(m.group()),svg);target.write_text(svg)
        else:shutil.copyfile(src,target)
    # Publish reproducible trial configs and the checkpoints' optimizer/RNG metadata.
    for directory in ['configs','checkpoints']:
        for src in (run/directory).rglob('*'):
            if not src.is_file() or '.partial' in src.name or src.suffix not in {'.json','.zip','.pkl'}:continue
            target=dest/src.relative_to(run);target.parent.mkdir(parents=True,exist_ok=True)
            if src.suffix=='.json':write(target,clean(read(src)))
            else:shutil.copyfile(src,target)
    m['report']=None
    if (run/'report.json').exists():
        report=clean(read(run/'report.json'));write(dest/'report.json',report);public_report(dest,report);m['report']=f'artifacts/{run.name}/report.html'
    write(dest/'state.json',m['state']);write(dest/'manifest.json',m)
    write(output/'experiments/index.json',{'runs':[{'run_id':run.name,'started_at':m['run']['started_at'],'manifest':f'artifacts/{run.name}/manifest.json'}],'updated_at':exported_at})
    write(output/'timeline.json',clean(read(ROOT/'site/timeline.json')))
    for name in ['PLAN','HANDOFF']:
        src=ROOT/'site'/f'{name}.txt'
        if src.exists():(output/f'{name}.txt').write_text(clean(src.read_text()))
    write(output/'publication.json',m['publication'])
    return m
def build(output):
    if output.exists():shutil.rmtree(output)
    output.mkdir(parents=True)
    for p in (ROOT/'site').iterdir():
        if p.is_file() and p.suffix in {'.html','.css','.js','.svg','.ico'}:shutil.copyfile(p,output/p.name)
    shutil.copytree(ROOT/'public',output,dirs_exist_ok=True)
    (output/'.nojekyll').touch()
    if any(p.is_symlink() for p in output.rglob('*')):raise ValueError('Pages artifact contains a symlink')
    return output
def audit(root):
    for p in root.rglob('*'):
        if not p.is_file() or p.suffix not in {'.json','.jsonl','.txt','.html','.svg','.md','.js','.css'}:continue
        text=p.read_text()
        if SECRET.search(text) or ('/Users/'+Path.home().name) in text or any(n in text for n in LOCAL_NAMES):raise ValueError(f'Private material: {p}')
        if p.suffix=='.json':
            def keys(v):
                if isinstance(v,dict):
                    for k,a in v.items():
                        if k in {'quota','quota_start','quota_latest','used_percent','resets_at','pid'}:raise ValueError(f'Private key {k}: {p}')
                        keys(a)
                elif isinstance(v,list):
                    for a in v:keys(a)
            keys(read(p))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path);ap.add_argument('--build',type=Path);a=ap.parse_args()
    if a.run:
        # Failed audits never replace a previously reviewed public snapshot.
        with tempfile.TemporaryDirectory(prefix='.public-export-',dir=ROOT) as temporary:
            output=Path(temporary)/'snapshot';output.mkdir();m=export_run(a.run,output);audit(output)
            previous=Path(temporary)/'previous';public=ROOT/'public'
            if public.exists():os.replace(public,previous)
            try:os.replace(output,public)
            except Exception:
                if previous.exists():os.replace(previous,public)
                raise
        print(f'Exported {len(m["intervals"])} intervals at {m["publication"]["exported_at"]}')
    if a.build:build(a.build);audit(a.build);print(f'Pages artifact ready: {a.build}')
if __name__=='__main__':main()
