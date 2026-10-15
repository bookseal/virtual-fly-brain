"""One serialized HyperFrames render queue; interval cards are already published."""
import argparse,html,os,shutil,subprocess,time,signal,re,functools
from pathlib import Path
from .store import *
CLI=ROOT/'video/node_modules/.bin/hyperframes';TEMPLATE=ROOT/'video/interval-template'
def h(s):return html.escape(str(s))
def composition(run,row,dest,duration=24):
    dest.mkdir(parents=True,exist_ok=True)
    if not (dest/'assets').exists():(dest/'assets').symlink_to(TEMPLATE/'assets',target_is_directory=True)
    for name in ['hyperframes.json','BRIEF.md','design.md']:
        if (TEMPLATE/name).resolve()!=(dest/name).resolve():shutil.copy(TEMPLATE/name,dest/name)
    ev=row.get('evaluation') or {};source=ev.get('video');media='';video_layer='';caption='진행 상태 카드 · 행동 평가 없음'
    if source:
        original=ROOT/'site'/source
        if original.exists():
            shutil.copy(original,dest/'behavior.mp4');media='<div class="video-placeholder"></div>';caption=f"실제 {ev.get('backend','')} 평가 / {ev.get('policy','')} / {ev.get('evaluated_at','')} / seed {ev.get('video_seed','')}"
    if not media:
        original=ROOT/'site'/row['media'][0];shutil.copy(original,dest/'status.svg');media='<img src="status.svg" alt="실행 상태 기록">'
    figure=''
    if ev.get('path_image'):
        shutil.copy(ROOT/'site'/ev['path_image'],dest/'paths.png');figure='<img class="paths" src="paths.png" alt="실측 경로">'
    start2=duration*.25;start3=duration*2/3
    if source and (dest/'behavior.mp4').exists():
        length=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(dest/'behavior.mp4')]))
        shown=min(length,start3-start2)
        video_layer=f'<video id="actual-footage" class="clip actual-footage" src="behavior.mp4" muted playsinline data-start="{start2}" data-duration="{shown}" data-track-index="1"></video>'
        if shown<start3-start2:
            subprocess.run(['ffmpeg','-y','-sseof','-0.05','-i',str(dest/'behavior.mp4'),'-frames:v','1',str(dest/'last-frame.png'),'-loglevel','error'],check=True)
            video_layer+=f'<img id="last-evaluation-frame" class="clip actual-footage" src="last-frame.png" alt="실제 평가의 마지막 프레임" data-start="{start2+shown}" data-duration="{start3-start2-shown}" data-track-index="1">'
            caption+=' · 재생 뒤에는 마지막 프레임 표시'
    metric=f"{round(ev['success_rate']*100)}% · {ev['episodes']}회 평가" if ev else '아직 성능을 판정하지 않았습니다'
    doc='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=1280,height=720"><script src="assets/gsap.min.js"></script><style>
@font-face{font-family:Noto;src:url('assets/NotoSansKR.ttf')}*{box-sizing:border-box}html,body{margin:0;width:1280px;height:720px;overflow:hidden;background:#f7f8fa;color:#22313e;font-family:Noto,sans-serif}#root{width:100%;height:100%;position:relative;overflow:hidden}.clip{position:absolute;inset:0;background:#f7f8fa;padding:56px}.eyebrow{font-size:20px;letter-spacing:2px;color:#b54424}.question{font-size:49px;line-height:1.45;max-width:1100px;margin:62px 0 20px;word-break:keep-all}.subtitle{font-size:27px;line-height:1.6;color:#536575;max-width:1100px}.title{font-size:28px;margin:24px 0}.evidence{display:flex;gap:24px;margin-top:24px;height:460px}.video-placeholder{width:720px;flex-shrink:0}.actual-footage{inset:auto;left:56px;top:110px;width:720px;height:430px;object-fit:contain;padding:0;background:#eef0f2}.evidence video,.evidence>img{width:720px;height:430px;object-fit:contain;background:#eef0f2}.evidence .paths{width:390px;height:330px}.caption{position:absolute;bottom:50px;left:56px;right:56px;font-size:19px;color:#536575}.metric{font-size:36px;color:#b54424;margin-top:30px}.outcome{font-size:34px;line-height:1.5;margin:40px 0 32px;max-width:1130px;word-break:keep-all}.next{font-size:29px;line-height:1.6;color:#536575;max-width:1130px;word-break:keep-all}.progress{position:absolute;bottom:0;left:0;height:8px;background:#b54424;width:1280px;transform-origin:left center}
</style></head><body>'''
    doc+=f'<div id="root" data-composition-id="main" data-width="1280" data-height="720" data-duration="{duration}">'
    doc+=f'<section id="scene-question" class="clip" data-start="0" data-duration="{start2}" data-track-index="0"><div id="opening"><div class="eyebrow">FLY BRAIN LAB / +{row["elapsed_minutes"]:.0f}분 / {h(row.get("backend"))}</div><h1 class="question">{h(row["question"])}</h1><p class="subtitle">{h(row["change"])}</p></div></section>'
    doc+=f'<section id="scene-evidence" class="clip" data-start="{start2}" data-duration="{start3-start2}" data-track-index="0"><div class="eyebrow">확보된 근거 / {h(metric)}</div><div class="evidence">{media}{figure}</div><p class="caption">{h(caption)} · 마지막 평가 시각 기준</p></section>'
    doc+=f'<section id="scene-result" class="clip" data-start="{start3}" data-duration="{duration-start3}" data-track-index="0"><div id="ending"><div class="eyebrow">관찰 → 다음 선택</div><p class="outcome">{h(row["result"])}</p><p class="next">다음: {h(row["next_action"])}</p><p class="subtitle">기록 {h(row["recorded_at"])}</p></div></section>{video_layer}<div class="progress" id="progress"></div></div>'
    doc+=f'<script>const tl=gsap.timeline({{paused:true}});tl.from("#opening",{{y:20,opacity:0,duration:.6}},0);tl.from("#ending",{{y:20,opacity:0,duration:.6}},{start3});tl.fromTo("#progress",{{scaleX:0}},{{scaleX:1,duration:{duration},ease:"none"}},0);window.__timelines["main"]=tl;</script></body></html>'
    (dest/'index.html').write_text(doc);return dest

def patch_interval(run,p,patch):
    with lock(run/'.snapshot.lock'):
        row=read(p,{})
        if patch.get('status')=='rendering' and row.get('render',{}).get('status') in ['failed','done']:
            row.setdefault('render_history',[]).append(row['render'])
        row['render']=patch;atomic(p,row)
    publish(run)

def run_checked(command,log,timeout,env=None):
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
    try:
        code=process.wait(timeout=timeout)
        if code:raise subprocess.CalledProcessError(code,command)
    except subprocess.TimeoutExpired:
        # The entire isolated render process group belongs to this job.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait();raise

def serialized_render(fn):
    @functools.wraps(fn)
    def wrapped(*args,**kwargs):
        with lock(ROOT/'runs/.global-render.lock'):return fn(*args,**kwargs)
    return wrapped

@serialized_render
def render_one(run,p,check=True,kind='interval'):
    row=read(p);dest=run/'videos'/f'{kind}-{row["index"]:04d}';dest.mkdir(parents=True,exist_ok=True)
    output=dest/'recap.mp4'
    if output.exists():
        archive=dest/'superseded';archive.mkdir(exist_ok=True);shutil.copy(output,archive/f'{time.time_ns()}.mp4')
    patch_interval(run,p,{'status':'rendering','started_at':now()})
    env={**os.environ,'HYPERFRAMES_RENDER_DETACHED':'1','DO_NOT_TRACK':'1'}
    log=dest/'render.log'
    try:
        composition(run,row,dest,duration=40 if kind=='hour' else 24)
        with log.open('a') as f:
            if check:run_checked([str(CLI),'check',str(dest),'--timeout','30000'],f,180,env)
            run_checked([str(CLI),'render',str(dest),'--output',str(output),'--fps','24','--quality','delivery','--workers','1'],f,540,env)
        meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size','-of','json',str(output)]))
        if float(meta['format']['duration'])<23:raise RuntimeError('render shorter than 23 seconds')
        patch_interval(run,p,{'status':'done','completed_at':now(),'video':asset(run,output),'probe':meta,'composition':asset(run,dest/'index.html')})
    except Exception as exc:
        patch_interval(run,p,{'status':'failed','failed_at':now(),'error':str(exc),'log':asset(run,log)});event(run,'error','구간 영상 렌더 실패',interval=row['index'],detail=str(exc))

def summaries(run):
    cfg=read(run/'run.json');hours=int((time.time()-cfg['started_epoch'])//3600)
    rows=[read(p) for p in sorted((run/'intervals').glob('*.json'))]
    for hour in range(1,hours+1):
        p=run/'summaries'/f'hour-{hour:02d}.json'
        if p.exists():continue
        group=[r for r in rows if (hour-1)*3600 < r['scheduled_epoch']-cfg['started_epoch']<=hour*3600]
        if not group:continue
        first,last=group[0],group[-1];row=dict(last);row.update(index=hour,question=f'{hour}번째 한 시간 동안 무엇이 달라졌을까?',change=f'구간 {first["index"]} → {last["index"]}. '+last['change'],result=last['result']+f' 이 시간의 기록 지연 {sum(r.get("status")=="gap" for r in group)}개.',render={'status':'queued'},summary_kind='hour',source_intervals=[r['id'] for r in group]);atomic(p,row)
    for p in sorted((run/'summaries').glob('hour-*.json')):
        if read(p).get('render',{}).get('status')=='queued':render_one(run,p,kind='hour');return

@serialized_render
def retrospective(run,public_only=False):
    marker=run/('retrospective-public.json' if public_only else 'retrospective.json')
    if read(marker,{}).get('status') in ['done','failed']:return
    rows=[read(p) for p in sorted((run/'intervals').glob('*.json'))];rows=[r for r in rows if r.get('render',{}).get('status')=='done']
    if public_only:rows=[r for r in rows if not re.search(r'구독|주간.{0,20}(한도|사용)|시작 시 주간|account/rateLimits|used_percent|resets_at',str(r.get('result','')))]
    if not rows:return
    # Preserve chronological order; include start, known failures, evaluation changes and end.
    important=[0,len(rows)-1]+[i for i,r in enumerate(rows) if r.get('status')=='gap' or r.get('evaluation') and (i==0 or rows[i-1].get('evaluation',{} )!=r.get('evaluation'))]
    def spaced(n,k):return [round(i*(n-1)/(k-1)) for i in range(k)]
    important+=spaced(len(rows),10);chosen=sorted(set(important))
    if len(chosen)>10:chosen=[chosen[i] for i in spaced(len(chosen),10)]
    selected=[rows[i] for i in chosen];dest=run/'videos'/('retrospective-public' if public_only else 'retrospective');dest.mkdir(parents=True,exist_ok=True);duration=len(selected)*24
    # If fewer than eight interval videos exist, say the run was too short; never pad fake history.
    if duration<180:atomic(marker,{'status':'failed','reason':'Fewer than 8 usable interval videos; full 3–5 minute recap not supported by evidence'});return
    (dest/'assets').symlink_to(TEMPLATE/'assets',target_is_directory=True) if not (dest/'assets').exists() else None
    clips=''
    for i,r in enumerate(selected):
        shutil.copy(ROOT/'site'/r['render']['video'],dest/f'part-{i}.mp4');clips+=f'<video id="part-{i}" class="clip" src="part-{i}.mp4" muted data-start="{i*24}" data-duration="24" data-track-index="0"></video>'
    (dest/'index.html').write_text(f'<html lang="ko"><head><meta charset="utf-8"><script src="assets/gsap.min.js"></script><style>html,body{{margin:0;width:1280px;height:720px;background:#f7f8fa}}#root{{width:100%;height:100%;position:relative}}.clip{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}}</style></head><body><div id="root" data-composition-id="main" data-width="1280" data-height="720" data-duration="{duration}">{clips}</div><script>window.__timelines["main"]=gsap.timeline({{paused:true}});</script></body></html>')
    atomic(marker,{'status':'rendering','source_intervals':[r['id'] for r in selected]});output=dest/'retrospective.mp4'
    try:
        with (dest/'render.log').open('w') as f:
            run_checked([str(CLI),'check',str(dest)],f,240)
            run_checked([str(CLI),'render',str(dest),'--output',str(output),'--workers','1','--fps','24','--quality','delivery'],f,2400,{**os.environ,'HYPERFRAMES_RENDER_DETACHED':'1'})
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size','-of','json',str(output)]));atomic(marker,{'status':'done','at':now(),'video':asset(run,output),'probe':probe,'source_intervals':[r['id'] for r in selected]})
    except Exception as exc:atomic(marker,{'status':'failed','at':now(),'error':str(exc),'log':asset(run,dest/'render.log')})
    publish(run)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('--once',action='store_true');a=ap.parse_args();run=Path(a.run).resolve()
    stop={'value':False}
    signal.signal(signal.SIGTERM,lambda *_:stop.update(value=True))
    with lock(run/'.video-worker.lock'):
        atomic(run/'video-worker.json',{'pid':os.getpid(),'at':now()})
        # Recovery: only this lock owner can have an active render.
        for p in (run/'intervals').glob('*.json'):
            if read(p).get('render',{}).get('status')=='rendering':patch_interval(run,p,{'status':'queued','reason':'renderer restarted'})
        while not stop['value']:
            pending=[p for p in sorted((run/'intervals').glob('*.json')) if read(p).get('render',{}).get('status')=='queued']
            if pending:render_one(run,pending[0])
            elif a.once:break
            elif read(run/'state.json',{}).get('status') in ['completed','stopped','failed'] and (run/'final-recorded.json').exists():
                summaries(run);retrospective(run)
                from .report import build_report
                build_report(run);publish(run);break
            else:summaries(run);time.sleep(5)
            if a.once:break
if __name__=='__main__':main()
