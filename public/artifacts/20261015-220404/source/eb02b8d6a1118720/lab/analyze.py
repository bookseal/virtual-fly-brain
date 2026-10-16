"""Evidence-only analysis of completed evaluations; no learning or model selection."""
import argparse
from pathlib import Path
import numpy as np
from .store import read,atomic,now,asset,publish

def analyze(run):
    records=[read(p) for p in sorted((run/'evaluations').glob('*.json'))]
    rows=[]
    for e in records:
        if e.get('backend')!='3d' or e.get('task')!='food-near' or e.get('selection_holdout'):continue
        if e['policy'] not in ['untrained','bc-initial','ppo','bc-ppo']:continue
        episodes=e['episodes_raw'];actions=np.array([a for r in episodes for a in r['actions']])
        rows.append({'seed':e['seed'],'policy':e['policy'],'route':'bc-ppo' if e['policy'].startswith('bc-') else 'ppo','timesteps':e['timesteps'],'evaluated_at':e['evaluated_at'],'successes':e['successes'],'episodes':e['episodes'],'success_rate':e['success_rate'],'mean_return':float(np.mean([r['reward'] for r in episodes])),'mean_final_distance_mm':float(np.mean([np.linalg.norm(np.array(r['path'][-1])-r['target']) for r in episodes])),'mean_control':actions.mean(0).tolist(),'mean_steps':float(np.mean([r['steps'] for r in episodes])),'numerical_failures':sum(bool(r['info'].get('numerical_failure') or r.get('error')) for r in episodes),'record_url':e['record_url'],'video':e.get('video'),'video_seed':e.get('video_seed'),'path_image':e.get('path_image'),'config':e['config']})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font=Path(__file__).resolve().parents[1]/'video/interval-template/assets/NotoSansKR.ttf'
    if font.exists():
        font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True)
    fig.patch.set_facecolor('#f6f3eb')
    for col,seed in enumerate([11,29]):
        for route,color,label in [('ppo','#b64a28','PPO 단독'),('bc-ppo','#27594b','모방 후 PPO')]:
            subset=sorted([r for r in rows if r['seed']==seed and r['route']==route and r['timesteps']<=10240],key=lambda r:r['timesteps'])
            # This is the first-budget diagnosis, not a moving headline about
            # every future model. Never connect differing failure protocols.
            protocols=sorted({r['config'].get('physics_error_policy','raise') for r in subset})
            for protocol_index,protocol in enumerate(protocols):
                group=[r for r in subset if r['config'].get('physics_error_policy','raise')==protocol]
                x=[r['timesteps'] for r in group]
                plot_label=label+(' · 오류 복구 적용' if protocol=='terminate' else '')
                axes[0,col].plot(x,[100*r['success_rate'] for r in group],'o-' if protocol_index==0 else 's--',color=color,label=plot_label)
                axes[1,col].plot(x,[r['mean_return'] for r in group],'o-' if protocol_index==0 else 's--',color=color,label=plot_label)
        axes[0,col].set_title(f'학습 seed {seed} · 같은 평가 조건 20개')
        axes[0,col].set_ylim(-5,105);axes[0,col].set_ylabel('먹이에 도착한 비율 (%)');axes[0,col].legend()
        axes[1,col].set_ylabel('평가 보상 합계의 평균');axes[1,col].set_xlabel('몸으로 직접 행동한 횟수')
        for ax in axes[:,col]:ax.grid(alpha=.2);ax.set_facecolor('#fffefa')
    fig.suptitle('첫 10,240회 비교: 점수는 높아졌지만, 도착 횟수는 줄었습니다',fontsize=15)
    fig.tight_layout(rect=[0,0,1,.95]);path=run/'media/reward-versus-arrival.png';fig.savefig(path,dpi=150);plt.close(fig)
    result={'at':now(),'title':'점수가 오르는데, 왜 먹이에는 도착하지 못할까?','chart':asset(run,path),'comparison_budget':10240,'measurement':'이 차트는 첫 10,240회까지의 비교를 보존합니다. 같은 20개 평가 조건에서 성공률과 에피소드 보상 합계를 따로 계산했습니다. 학습 중 로그의 점수가 아니라 저장된 평가의 실제 결과입니다.','interpretation':'PPO 단독은 점수 손실을 줄였지만 도달률은 낮아졌습니다. 현재 해석은 멀리 벗어나는 행동을 줄이는 쪽으로 학습하면서, 도착에 필요한 움직임까지 줄였을 수 있다는 것입니다. 원인 확정은 별도 변경 실험이 필요합니다.','next_action':'기존 A/B 비교를 보존하고, 초기 행동 탐험 폭만 바꾸는 진단을 별도 표에서 비교합니다.','rows':rows,'limit':'같은 20개 조건을 반복 평가했습니다. 새로운 30개 조건과 세 번째 학습 seed의 검증은 아직 필요합니다.'}
    atomic(run/'analysis.json',result);publish(run);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');a=p.parse_args();d=analyze(Path(a.run).resolve());print('analyzed',len(d['rows']),'completed evaluations')
