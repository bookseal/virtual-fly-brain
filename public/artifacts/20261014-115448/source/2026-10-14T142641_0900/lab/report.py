import argparse,html,json,time
from pathlib import Path
from .store import *
def build_report(run):
    run=Path(run);cfg=read(run/'run.json');rows=[read(p) for p in sorted((run/'evaluations').glob('*.json'))];snaps=[read(p) for p in sorted((run/'intervals').glob('*.json'))];q=read(run/'quota.json',{});smoke=read(run/'smoke3d.json',{});comparisons=[]
    for trial in sorted(set(r['trial'] for r in rows)):
        rs=[r for r in rows if r['trial']==trial];before=next((r for r in rs if r['policy']=='untrained'),None);after=[r for r in rs if r['policy']=='ppo' and not r.get('selection_holdout')]
        if before and after:
            last=after[-1];comparisons.append({'trial':trial,'backend':last['backend'],'before':before['success_rate'],'after':last['success_rate'],'change_pp':round(100*(last['success_rate']-before['success_rate']),1),'fixed_episodes':last['episodes'],'comparable_seeds':before['evaluation_suite']==last['evaluation_suite'],'before_record':before['record_url'],'after_record':last['record_url'],'holdout':[{k:r[k] for k in ['success_rate','episodes','record_url']} for r in rs if r.get('selection_holdout')]})
    errors=[e for e in events(run) if e['kind']=='error'];improvements=[c for c in comparisons if c['change_pp']>0 and c['comparable_seeds']];obs=[r for r in rows if r['task'].startswith('obstacles') and r.get('selection_holdout')]
    verdict={'record_system':{'status':'pass' if snaps and not any(s.get('status')=='gap' for s in snaps) else 'partial','intervals':len(snaps),'rendered':sum(s.get('render',{}).get('status')=='done' for s in snaps),'gaps':sum(s.get('status')=='gap' for s in snaps)},'3d_execution':{'status':'pass' if smoke.get('video') else 'not_confirmed','evidence':smoke.get('video')},'learning_improvement':{'status':'observed' if improvements else 'not_confirmed','comparisons':comparisons,'interpretation':'同条件の観測差'.replace('同条件の観測差','같은 조건에서 관측한 차이이며 통계적 확정이나 생물학적 학습의 재현을 뜻하지 않습니다.')},'obstacles':{'status':'observed' if any(r['success_rate']>=.7 for r in obs) else ('not_confirmed' if obs else 'not_started'),'holdout_results':[{k:r[k] for k in ['success_rate','episodes','record_url']} for r in obs]}}
    out={'run_id':run.name,'generated_at':now(),'elapsed_hours':(time.time()-cfg['started_epoch'])/3600,'quota_start':cfg['quota_start'],'quota_latest':q,'verdict':verdict,'errors':errors,'remaining':['실제 초파리 뇌 전체와 생물학적 가소성은 이번 정책 학습의 대상이 아닙니다.','서로 다른 환경 seed와 새로운 조건에서 반복 검증이 필요합니다.'],'reproduction':'See EXPERIMENTS.md and per-evaluation config/seeds/checkpoint/actions.'}
    atomic(run/'report.json',out)
    esc=lambda x:html.escape(str(x))
    body=f'<h1>첫날 실험 보고서</h1><p>{esc(run.name)} · {esc(out["generated_at"])} · 실제 {out["elapsed_hours"]:.2f}시간</p><p>아래 판정은 실제 저장된 원본 기록으로만 계산합니다. 아직 진행 중이면 잠정 결과입니다.</p>'
    for key,item in verdict.items():body+=f'<h2>{esc(key)} — {esc(item["status"])}</h2><pre>{esc(json.dumps(item,ensure_ascii=False,indent=2))}</pre>'
    body+=f'<h2>원본 보고서</h2><a href="report.json">JSON</a><p><a href="/\u0023experiments">실험 타임라인으로 돌아가기</a></p>'
    (run/'report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>첫날 실험 보고서</title><style>body{font:17px/1.7 system-ui;max-width:1000px;margin:40px auto;padding:24px;color:#22313e;background:#f7f8fa}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:20px;border:1px solid #dae0e6}</style>'+body+'</html>')
    return out
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();build_report(Path(a.run).resolve())
