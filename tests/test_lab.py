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

def test_partial_resume_reaches_exact_comparison_budget(run):
    from lab.learning import train
    c={'trial':'partial','backend':'2d','task':'food','curriculum':'near','reward_mode':'dense','max_steps':12,'seed':11}
    a=train(run,c,170,1)
    b=train(run,c,256-170,1,a['checkpoint'])
    assert a['timesteps']==170 and b['timesteps']==256
    from stable_baselines3 import PPO
    assert PPO.load(b['checkpoint']).n_steps==128

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

def test_physics_failure_is_explicit_and_finite():
    from dm_control.rl.control import PhysicsError
    class BrokenPhysics:
        def step(self,action):raise PhysicsError('injected BADQACC')
    env=FoodEnv('2d',physics_error_policy='terminate');before,_=env.reset(seed=11);env.sim=BrokenPhysics()
    obs,reward,terminated,truncated,info=env.step([.8,.8])
    np.testing.assert_array_equal(obs,before)
    assert np.isfinite(obs).all() and terminated and not truncated
    assert not info['success'] and info['numerical_failure'] and info['flips']==0
    assert reward==sum(info['reward_terms'].values()) and info['failure_actions']==[[.8,.8]]
    env.physics_error_policy='raise'
    with pytest.raises(PhysicsError):env.step([.8,.8])
    class ProgrammingError:
        def step(self,action):raise ValueError('injected coding error')
    env.sim=ProgrammingError();env.physics_error_policy='terminate'
    with pytest.raises(ValueError):env.step([.8,.8])

def test_vector_training_records_physics_failures_and_continues(run,monkeypatch):
    from dm_control.rl.control import PhysicsError
    from stable_baselines3.common.vec_env import DummyVecEnv
    from lab import learning
    class BrokenPhysics:
        def step(self,action):raise PhysicsError('injected BADQACC')
    class InjectedEnv(FoodEnv):
        def reset(self,**kwargs):
            self.sim=None;out=super().reset(**kwargs);self.sim=BrokenPhysics();return out
        def close(self):pass
    monkeypatch.setattr(learning,'build_vec',lambda c,w:DummyVecEnv([lambda:InjectedEnv('2d',physics_error_policy='terminate')]))
    c={'trial':'recover','backend':'2d','task':'food','curriculum':'near','reward_mode':'dense','max_steps':12,'seed':11}
    result=learning.train(run,c,4,1)
    failures=[store.read(p) for p in (run/'failures').glob('*.json')]
    assert result['timesteps']==4 and len(failures)==4
    assert all(isinstance(r['info']['terminal_observation'],list) and not r['info']['success'] for r in failures)

def test_completed_evaluation_episode_survives_retry(run):
    from lab.learning import eval_worker
    progress=run/'progress'
    c={'backend':'2d','task':'food','curriculum':'near','max_steps':20}
    args=(c,[10000],'rule',None,None,str(progress))
    first=eval_worker(args)
    assert (progress/'10000.episode.json').exists()
    second=eval_worker(args)
    assert first==second

def test_supplementary_evaluation_keeps_primary_training_state(run):
    from lab.learning import evaluate
    store.update_state(run,status='training',activity='primary comparison',training={'timesteps':512})
    store.atomic(run/'latest-evaluation.json',{'id':'primary'})
    c={'trial':'diagnostic','backend':'2d','task':'food','curriculum':'wide','reward_mode':'dense','max_steps':4,'seed':11}
    result=evaluate(run,c,'rule',seeds=[30000],workers=1,tag='diagnostic',background=True)
    assert result['seeds']==[30000] and not result['selection_holdout']
    assert store.read(run/'state.json')['activity']=='primary comparison'
    assert store.read(run/'latest-evaluation.json')['id']=='primary'

def test_noise_ablation_changes_only_initial_log_std(run):
    import torch
    from stable_baselines3 import PPO
    from lab.learning import train
    c={'trial':'noise-control','backend':'2d','task':'food','curriculum':'near','reward_mode':'dense','max_steps':12,'seed':11,'action_mode':'normalized'}
    store.update_state(run,status='training',activity='primary')
    a=train(run,c,0,1,background=True)
    b=train(run,{**c,'trial':'noise-variant','initial_log_std':-1.},0,1,background=True)
    original=PPO.load(a['checkpoint']).policy.state_dict();variant=PPO.load(b['checkpoint']).policy.state_dict()
    import pickle
    with open(a['checkpoint'].removesuffix('.zip')+'.rng.pkl','rb') as f:rng=pickle.load(f)
    assert rng['env'][0]==np.random.default_rng(11).bit_generator.state
    assert torch.equal(variant['log_std'],torch.full((2,),-1.))
    for key in original:
        if key!='log_std':assert torch.equal(original[key],variant[key]),key
    train(run,{**c,'trial':'background-training'},128,1,background=True)
    assert store.read(run/'state.json')['activity']=='primary'
    assert not (run/'trainer-heartbeat.json').exists()

def test_noise_campaign_pairs_early_results_and_keeps_holdout_last(run,monkeypatch):
    import pickle,sys
    from lab import noise_ablation as campaign
    store.atomic(run/'quota.json',{'gate':'continue'})
    for seed in (11,29):store.atomic(run/'configs'/f'3d-near-ppo-seed{seed}.json',{'seed':seed,'backend':'2d','trial':f'3d-near-ppo-seed{seed}'})
    calls=[]
    def fake_job(run,args,deadline):
        args=list(map(str,args));c=store.read(args[args.index('--config')+1]);trial=c['trial'];cp=campaign.latest_checkpoint(run,trial)
        steps=store.read(str(cp).removesuffix('.zip')+'.json',{}).get('timesteps',0) if cp else 0
        if args[0]=='train':
            steps+=int(args[args.index('--steps')+1]);path=run/'checkpoints'/trial/f'step-{steps:09d}'
            path.parent.mkdir(parents=True,exist_ok=True);path.with_suffix('.zip').write_bytes(b'fake model for orchestration test')
            store.atomic(str(path)+'.json',{'timesteps':steps})
            with open(str(path)+'.rng.pkl','wb') as f:pickle.dump({'env':[np.random.default_rng(c['seed']+i).bit_generator.state for i in range(2)]},f)
        else:
            holdout='--tag' in args;calls.append((trial,steps,holdout))
            store.atomic(run/'evaluations'/f'{len(calls):03d}.json',{'trial':trial,'timesteps':steps,'selection_holdout':holdout})
        return True
    monkeypatch.setattr(campaign,'job',fake_job)
    monkeypatch.setattr(campaign,'initial_equivalence',lambda *args:{'all_other_parameters_identical':True})
    monkeypatch.setattr(sys,'argv',['noise_ablation',str(run)])
    campaign.main()
    assert len(calls)==12
    assert [steps for _,steps,holdout in calls if not holdout]==[2048]*4+[10240]*4
    assert [holdout for _,_,holdout in calls]==[False]*8+[True]*4
    assert store.read(run/'noise-ablation.json')['status']=='completed'
    campaign.main()
    assert len(calls)==12, 'Restart must not repeat completed fixed or holdout evaluations'

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

def test_preview_byte_ranges(tmp_path):
    import threading,http.server,urllib.request,urllib.error
    from functools import partial
    from lab.server import RangeHandler
    (tmp_path/'clip.mp4').write_bytes(b'0123456789')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(RangeHandler,directory=str(tmp_path)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}/clip.mp4'
    try:
        for header,expected in [('bytes=2-5',b'2345'),('bytes=-3',b'789'),('bytes=7-',b'789')]:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':header})) as r:
                assert r.status==206 and r.read()==expected and r.headers['Accept-Ranges']=='bytes'
        with pytest.raises(urllib.error.HTTPError) as e:urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=99-'}))
        assert e.value.code==416
    finally:server.shutdown();server.server_close();thread.join()
