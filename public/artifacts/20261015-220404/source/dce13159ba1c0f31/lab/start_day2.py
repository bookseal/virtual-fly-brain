"""Create a reproducible day-two run; launch the approved local workers on request."""
import argparse,subprocess,time
from .store import *
from .quota import get_quota
from .manage import launch

def create():
    prior=read(RUNS/'active.json',{}).get('run_id')
    if prior and read(RUNS/prior/'state.json',{}).get('status') not in ['completed','failed','stopped']:
        raise RuntimeError(f'An unfinished run exists: {prior}. Inspect it before creating another.')
    stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S');run=RUNS/stamp;t=time.time();quota=get_quota()
    for name in ['media','intervals','summaries','evaluations','checkpoints','configs','logs','videos','trials','reviews']:(run/name).mkdir(parents=True,exist_ok=True)
    atomic(run/'run.json',dict(schema_version=2,run_id=stamp,started_at=now(),started_epoch=t,implementation_started_at=now(),base_hours=24,max_hours=24,interval_seconds=600,review_seconds=1800,summary_hours=2,model_requested='gpt-6.1-sol',reasoning='high',speed='default',quota_start=quota,reserve_percent=5,public_url='https://bookseal.github.io/virtual-fly-brain/',purpose='PPO 실패 진단 · 단독 학습과 모방 후 학습 비교',parent_run=prior))
    atomic(run/'quota.json',quota)
    for seed in (11,29,47):
        for route in ('ppo','bc-ppo'):
            trial=f'3d-near-{route}-seed{seed}'
            atomic(run/'configs'/f'{trial}.json',dict(trial=trial,backend='3d',task='food',curriculum='near',reward_mode='dense',max_steps=120,seed=seed,action_mode='normalized',environment_version='food-v2-action-affine',initialization='random' if route=='ppo' else 'behavior-cloning-from-rule'))
    update_state(run,status='preparing',backend='setup',activity='새 비교 회차 준비',question='같은 조건에서 PPO 단독과 모방 후 PPO는 어떻게 달라질까?',change='학습 seed 11·29·47, 실제 3D 몸에서 비교',result='아직 새 평가 결과가 없습니다.',next_action='규칙 시범 수집과 기준선 평가')
    event(run,'start','24시간 상한의 비교 회차 생성');snapshot(run,0);atomic(RUNS/'active.json',{'run_id':stamp});return run

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--start',action='store_true');a=ap.parse_args();run=create()
    if a.start:
        for module,marker in [('lab.recorder','recorder.json'),('lab.video','video-worker.json'),('lab.publisher','publisher.json')]:launch(run,module,marker)
        p=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-m','lab.imitation','collect',str(run),'--config',str(run/'configs/3d-near-bc-ppo-seed11.json'),'--workers','2'],stdout=(run/'logs/demonstrations.log').open('a'),stderr=subprocess.STDOUT,start_new_session=True)
        atomic(run/'demonstration-process.json',{'pid':p.pid,'at':now()});launch(run,'lab.campaign_v2','campaign-v2.json')
    print(run)
if __name__=='__main__':main()
