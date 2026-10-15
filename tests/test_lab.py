import json,time
from pathlib import Path
import numpy as np
import pytest
from lab import store
from lab.envs import FoodEnv,rule_action
@pytest.fixture
def run(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'ROOT',tmp_path)
    run=tmp_path/'runs/test';run.mkdir(parents=True)
    for n in ['intervals','media','evaluations','trials','checkpoints']: (run/n).mkdir()
    store.atomic(run/'run.json',{'run_id':'test','started_epoch':time.time(),'started_at':store.now()})
    store.update_state(run,status='preparing',backend='setup')
    return run

def test_no_duplicate_and_delayed_gap(run):
    store.event(run,'install','real event');a=store.snapshot(run,0,1);b=store.snapshot(run,0,1)
    assert a==b and len(list((run/'intervals').glob('*.json')))==1
    cfg=store.read(run/'run.json');cfg['started_epoch']=time.time()-100;store.atomic(run/'run.json',cfg)
    c=store.snapshot(run,1,1);assert c['status']=='gap' and c['evaluation'] is None
    assert c['recording_delay_seconds']>90

def test_render_state_does_not_hide_card(run):
    a=store.snapshot(run,0,1);assert a['render']['status']=='queued'
    assert (store.ROOT/'site'/a['media'][0]).name.endswith('.svg')
    a['render']={'status':'failed','error':'injected render failure'};store.atomic(run/'intervals/0000.json',a);store.publish(run)
    assert store.read(run/'manifest.json')['intervals'][0]['render']['status']=='failed'
    assert (run/'media/interval-0000.svg').exists()

def test_deterministic_replay_and_rule():
    def rollout(seed):
        e=FoodEnv('2d');o,_=e.reset(seed=seed);result=[]
        for _ in range(120):
            o,r,t,tr,info=e.step(rule_action(o));result.append([*o,r])
            if t or tr:break
        return np.array(result),info
    a,info=rollout(10000);b,_=rollout(10000);np.testing.assert_array_equal(a,b);assert info['success']

def test_obstacle_collision_and_reward():
    e=FoodEnv('2d',task='obstacles');e.reset(seed=1);e.target=np.array([8.,0.]);e.obstacle=np.array([4.,0.]);e.distance=8.
    for _ in range(20):_,r,t,tr,info=e.step([1,1])
    assert info['collisions']>0 and e.pos[0]<4
    assert r==sum(info['reward_terms'].values())

def test_rng_restore_next_episode():
    e=FoodEnv();e.reset(seed=9);s=e.export_rng();a,_=e.reset();e.restore_rng(s);b,_=e.reset();np.testing.assert_array_equal(a,b)

def test_checkpoint_optimizer_and_resume(run):
    from lab.learning import train
    c={'trial':'test','backend':'2d','task':'food','curriculum':'near','reward_mode':'dense','max_steps':60,'seed':11}
    a=train(run,c,256,1);b=train(run,c,128,1,a['checkpoint']);assert b['timesteps']>a['timesteps']
    import zipfile
    with zipfile.ZipFile(b['checkpoint']) as z:assert 'policy.optimizer.pth' in z.namelist()
    assert Path(b['checkpoint'].removesuffix('.zip')+'.rng.pkl').exists()

def test_quota_unavailable(monkeypatch):
    import lab.quota as quota
    def fail(*a,**kw):raise FileNotFoundError('injected')
    monkeypatch.setattr(quota.subprocess,'Popen',fail)
    assert quota.get_quota()['status']!='available'

def test_process_termination_and_resume(run):
    import subprocess,sys,signal
    from lab.learning import train
    c={'trial':'interrupt','backend':'2d','task':'food','curriculum':'near','reward_mode':'dense','max_steps':60,'seed':17}
    store.atomic(run/'config.json',c)
    p=subprocess.Popen([sys.executable,'-m','lab.learning','train',str(run),'--config',str(run/'config.json'),'--steps','10000000'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.time()+25
        while not (run/'trainer-heartbeat.json').exists() and time.time()<deadline:time.sleep(.1)
        assert (run/'trainer-heartbeat.json').exists()
        p.terminate();assert p.wait(timeout=15)==0
        saved=store.read(run/'trials/interrupt.json');assert saved['stopped']
        resumed=train(run,c,128,1,saved['checkpoint']);assert resumed['timesteps']>saved['timesteps']
    finally:
        if p.poll() is None:p.kill();p.wait()

def test_render_failure_keeps_original_evidence(run,monkeypatch):
    from lab import video
    monkeypatch.setattr(video,'TEMPLATE',Path(__file__).resolve().parents[1]/'video/interval-template');monkeypatch.setattr(video,'ROOT',store.ROOT);monkeypatch.setattr(video,'CLI',Path('/usr/bin/false'))
    (store.ROOT/'site').mkdir(exist_ok=True)
    (store.ROOT/'site/artifacts').symlink_to(store.ROOT/'runs',target_is_directory=True)
    store.snapshot(run,0,1);video.render_one(run,run/'intervals/0000.json')
    r=store.read(run/'intervals/0000.json');assert r['render']['status']=='failed';assert r['media']
    assert any(e['kind']=='error' for e in store.events(run))

def test_evaluation_checkpoint_seed_and_progress(run):
    from lab.learning import train,evaluate
    c={'trial':'eval-test','backend':'2d','task':'food','curriculum':'near','reward_mode':'dense','max_steps':12,'seed':11}
    saved=train(run,c,128,1)
    a=evaluate(run,c,'ppo',saved['checkpoint'],seeds=[10000,10001],workers=1)
    b=evaluate(run,c,'ppo',saved['checkpoint'],seeds=[10000,10001],workers=1)
    assert a['timesteps']==saved['timesteps'] and a['checkpoint_sha256']==b['checkpoint_sha256']
    assert a['evaluation_suite']==b['evaluation_suite']
    assert [r['path'] for r in a['episodes_raw']]==[r['path'] for r in b['episodes_raw']]
    assert len(list((run/'evaluation-progress').glob('*/*.episode.json')))==4
    assert len([p for p in (run/'evaluation-progress').glob('*/*.json') if not p.name.endswith('.episode.json')])==4

def test_normalized_actions_preserve_physical_control():
    a=FoodEnv('2d',action_mode='raw');b=FoodEnv('2d',action_mode='normalized')
    a.reset(seed=31);b.reset(seed=31)
    for action in [[.8,.8],[.4,1.2],[-.5,1.5]]:
        x=a.step(action);y=b.step(np.array(action)-.5)
        np.testing.assert_allclose(x[0],y[0],atol=1e-6)
        np.testing.assert_allclose(a.actions[-1],b.actions[-1])
    assert b.policy_actions[-1]==[-1.,1.]

def test_completed_evaluation_episode_survives_retry(run):
    from lab.learning import eval_worker
    progress=run/'progress'
    c={'backend':'2d','task':'food','curriculum':'near','max_steps':20}
    args=(c,[10000],'rule',None,None,str(progress))
    first=eval_worker(args)
    assert (progress/'10000.episode.json').exists()
    second=eval_worker(args)
    assert first==second

def test_imitation_initializes_policy_without_online_training(run):
    from lab.imitation import collect,clone
    c={'trial':'bc-test','backend':'2d','task':'food','curriculum':'near','reward_mode':'dense','max_steps':60,'seed':11,'action_mode':'normalized'}
    demo=collect(run,c,workers=1,episodes=10)
    result=clone(run,c,epochs=20)
    assert set(demo['train_seeds']).isdisjoint(demo['validation_seeds'])
    assert result['online_timesteps']==0 and result['train_samples']>0
    assert result['history'][-1]['validation_mse']<result['history'][0]['validation_mse']
    from stable_baselines3 import PPO
    model=PPO.load(result['checkpoint'])
    assert model.num_timesteps==0 and model.action_space.low.tolist()==[-1.,-1.]
