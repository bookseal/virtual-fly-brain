import argparse,html,json,time
from pathlib import Path
from .store import *

def paired_seed_results(rows):
    """Compare only equal online budgets and identical evaluation suites."""
    result=[]
    for steps in (10240,20480):
        pairs=[]
        for seed in (11,29,47):
            candidates=[r for r in rows if r.get('backend')=='3d' and r.get('task')=='food-near' and r.get('seed')==seed and r.get('timesteps')==steps and not r.get('selection_holdout')]
            a=next((r for r in reversed(candidates) if r['policy']=='ppo' and r.get('config',{}).get('initialization')=='random'),None)
            b=next((r for r in reversed(candidates) if r['policy']=='bc-ppo' and r.get('config',{}).get('initialization')=='behavior-cloning-from-rule'),None)
            if a and b and a['evaluation_suite']==b['evaluation_suite']:
                pairs.append({'seed':seed,'ppo':a['success_rate'],'bc_ppo':b['success_rate'],'difference_pp':round((b['success_rate']-a['success_rate'])*100,1),'records':[a['record_url'],b['record_url']]})
        result.append({'online_timesteps':steps,'completed_pairs':len(pairs),'planned_pairs':3,'pairs':pairs,'mean_difference_pp':round(sum(p['difference_pp'] for p in pairs)/len(pairs),1) if pairs else None})
    return result

def build_report(run):
    run=Path(run);cfg=read(run/'run.json');rows=[read(p) for p in sorted((run/'evaluations').glob('*.json'))];snaps=[read(p) for p in sorted((run/'intervals').glob('*.json'))];q=read(run/'quota.json',{});smoke=read(run/'smoke3d.json',{});comparisons=[]
    for trial in sorted(set(r['trial'] for r in rows)):
        rs=[r for r in rows if r['trial']==trial];before=next((r for r in rs if r['policy'] in ['untrained','bc-initial','transfer-initial']),None);after=[r for r in rs if r['policy'] in ['ppo','bc-ppo'] and not r.get('selection_holdout')]
        if before and after:
            last=after[-1];comparisons.append({'trial':trial,'backend':last['backend'],'initial_policy':before['policy'],'before':before['success_rate'],'after':last['success_rate'],'change_pp':round(100*(last['success_rate']-before['success_rate']),1),'fixed_episodes':last['episodes'],'comparable_seeds':before['evaluation_suite']==last['evaluation_suite'],'before_record':before['record_url'],'after_record':last['record_url'],'holdout':[{k:r[k] for k in ['success_rate','episodes','record_url']} for r in rs if r.get('selection_holdout')]})
    if not smoke.get('video'):
        smoke=next((r for r in rows if r.get('backend')=='3d' and r.get('video')),(read(run/'diagnostics.json',{}).get('rows') or [{}])[0])
    errors=[e for e in events(run) if e['kind']=='error'];improvements=[c for c in comparisons if c['change_pp']>0 and c['comparable_seeds']];obs=[r for r in rows if r['task'].startswith('obstacles') and r.get('selection_holdout')]
    verdict={'record_system':{'status':'pass' if snaps and not any(s.get('status')=='gap' or s.get('render',{}).get('status')!='done' for s in snaps) else 'partial','intervals':len(snaps),'rendered':sum(s.get('render',{}).get('status')=='done' for s in snaps),'gaps':sum(s.get('status')=='gap' for s in snaps)},'3d_execution':{'status':'pass' if smoke.get('video') else 'not_confirmed','evidence':smoke.get('video')},'learning_improvement':{'status':'observed' if improvements else 'not_confirmed','comparisons':comparisons,'interpretation':'同条件の観測差'.replace('同条件の観測差','같은 조건에서 관측한 차이이며 통계적 확정이나 생물학적 학습의 재현을 뜻하지 않습니다.')},'obstacles':{'status':'observed' if any(r['success_rate']>=.7 for r in obs) else ('not_confirmed' if obs else 'not_started'),'holdout_results':[{k:r[k] for k in ['success_rate','episodes','record_url']} for r in obs]}}
    out={'run_id':run.name,'generated_at':now(),'elapsed_hours':(read(run/'state.json',{}).get('ended_epoch',time.time())-cfg['started_epoch'])/3600,'quota_start':cfg['quota_start'],'quota_latest':q,'verdict':verdict,'errors':errors,'remaining':['실제 초파리 뇌 전체와 생물학적 가소성은 이번 정책 학습의 대상이 아닙니다.','서로 다른 환경 seed와 새로운 조건에서 반복 검증이 필요합니다.'],'reproduction':'See README.md and per-evaluation config/seeds/checkpoint/actions.', 'publication':read(run/'deployment.json',{})}
    if cfg.get('schema_version',1)>=2:
        paired=paired_seed_results(rows)
        out['verdict']['replication']={'status':'observed' if any(p['completed_pairs']==3 for p in paired) else 'not_confirmed','matched_budgets':paired,'interpretation':'같은 온라인 행동 예산과 평가 조건에서만 seed별 차이를 계산합니다. B 경로는 별도 시범 비용이 있으며, 세 seed의 차이를 통계적 확정으로 해석하지 않습니다.'}
    atomic(run/'report.json',out)
    esc=lambda x:html.escape(str(x))
    body=f'<h1>실험 비교 보고서</h1><p>{esc(run.name)} · {esc(out["generated_at"])} · 실제 {out["elapsed_hours"]:.2f}시간</p><p>아래 판정은 실제 저장된 원본 기록으로만 계산합니다. 아직 진행 중이면 잠정 결과입니다.</p>'
    labels={'record_system':'10분 시각 기록','3d_execution':'실제 3D 몸 실행','learning_improvement':'정책의 학습 개선','obstacles':'장애물 회피 확장'}
    states={'pass':'확보','partial':'일부 지연 있음','observed':'관측됨','not_confirmed':'아직 확인되지 않음','not_started':'아직 시작하지 않음'}
    descriptions={'record_system':f"구간 {len(snaps)}개, 렌더 완료 {verdict['record_system']['rendered']}개, 기록 지연 {verdict['record_system']['gaps']}개. 늦게 저장된 구간은 연속 실행으로 표현하지 않습니다.",'3d_execution':'FlyGym과 MuJoCo로 다리가 있는 실제 3D 몸을 실행한 영상의 존재를 확인합니다.','learning_improvement':'같은 먹이 위치와 시작 조건에서 학습 전과 후의 도달 횟수를 비교합니다.','obstacles':'먹이 도달 기준을 충족한 뒤에만 장애물 과제를 별도로 평가합니다.'}
    labels['replication']='세 학습 seed에서 같은 학습량 비교';descriptions['replication']='같은 평가 조건과 행동 예산에서 A와 B 경로를 모두 완료한 seed만 비교합니다. 미완료 결과는 평균에 넣지 않습니다.'
    for key,item in verdict.items():body+=f'<section><h2>{esc(labels[key])} — {esc(states[item["status"]])}</h2><p>{esc(descriptions[key])}</p></section>'
    if comparisons:
        body+='<h2>같은 조건에서의 변화</h2><table><tr><th>실험</th><th>학습 전</th><th>학습 후</th><th>변화</th><th>새 조건 평가</th></tr>'
        for c in comparisons:
            holdout=', '.join(f"{r['success_rate']:.0%} / {r['episodes']}회" for r in c['holdout']) or '아직 없음'
            body+=f'<tr><td>{esc(c["trial"])}</td><td><a href="/{esc(c["before_record"])}">{c["before"]:.0%}</a></td><td><a href="/{esc(c["after_record"])}">{c["after"]:.0%}</a></td><td>{c["change_pp"]:+.1f}%p</td><td>{esc(holdout)}</td></tr>'
        body+='</table><p>20회 평가의 차이는 이번 조건에서의 관측입니다. 다른 seed와 새로운 조건의 결과를 함께 확인해야 합니다.</p>'
    body+=f'<h2>시간과 구독 사용량</h2><p>실제 경과 {out["elapsed_hours"]:.2f}시간. 시작 {cfg["quota_start"].get("used_percent","미확인")}% → 마지막 조회 {q.get("used_percent","미확인")}%. 증가 {q.get("increase_pp","미확인")}%p. 조회 시각 {esc(q.get("read_at","미확인"))}.</p>'
    body+='<h2>오류와 다음 확인</h2><ul>'+''.join(f'<li>{esc(e["at"])} · {esc(e["title"])}</li>' for e in errors)+'</ul><p>실제 초파리 뇌 전체 또는 생물학적 학습을 재현한 실험은 아닙니다.</p>'
    body+=f'<h2>원본 보고서</h2><a href="report.json">JSON</a><p><a href="/\u0023experiments">실험 타임라인으로 돌아가기</a></p>'
    (run/'report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>실험 비교 보고서</title><style>body{font:17px/1.7 system-ui;max-width:1000px;margin:40px auto;padding:24px;color:#22313e;background:#f7f8fa}section{background:white;padding:12px 24px;border:1px solid #dae0e6;margin:16px 0;border-radius:12px}table{display:block;overflow-x:auto;width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #dae0e6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:20px;border:1px solid #dae0e6}</style>'+body+'</html>')
    return out
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();build_report(Path(a.run).resolve())
