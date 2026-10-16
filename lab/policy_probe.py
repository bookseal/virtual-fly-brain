"""Query saved actors on explicitly hypothetical inputs, without a simulator."""
import argparse,hashlib,math
from pathlib import Path
import numpy as np
from .store import read,atomic,now,asset,publish,preserve_source
from .envs import rule_action

def input_grid():
    cases=[];observations=[]
    for distance in (1.5,3.,7.):
        for speed in (0.,6.,12.):
            for degrees in range(-40,41,5):
                angle=math.radians(degrees)
                obs=[distance*math.cos(angle)/16,distance*math.sin(angle)/16,distance/16,speed/20,0.,0.,0.,1.]
                cases.append({'food_angle_degrees':degrees,'distance_mm':distance,'speed_mm_per_second':speed,'turn_speed':0.})
                observations.append(obs)
    return cases,np.asarray(observations,dtype=np.float32)

def query(model,observations):
    import torch
    with torch.no_grad():
        distribution=model.policy.get_distribution(torch.tensor(observations,dtype=torch.float32)).distribution
        mean=distribution.mean.numpy();std=distribution.stddev.numpy()
        clipping=distribution.cdf(torch.full_like(distribution.mean,-1))+(1-distribution.cdf(torch.ones_like(distribution.mean)))
    predicted,_=model.predict(observations,deterministic=True)
    np.testing.assert_allclose(predicted,np.clip(mean,-1,1),atol=1e-6)
    return [{'normalized_mean':m.tolist(),'physical_signal':(p+.5).tolist(),'policy_std':s.tolist(),'expected_clipping_fraction':float(c.mean())} for m,p,s,c in zip(mean,predicted,std,clipping)]

def probe(run):
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(1);run=Path(run);cases,observations=input_grid();models=[]
    for seed in (11,29):
        for route in ('ppo','bc-ppo'):
            for steps in (0,10240):
                cp=run/'checkpoints'/f'3d-near-{route}-seed{seed}'/f'step-{steps:09d}.zip'
                if not cp.exists():continue
                config=read(cp.with_suffix('.json'))['config']
                if config.get('action_mode')!='normalized':raise ValueError('Probe expects normalized action checkpoints')
                values=query(PPO.load(cp,device='cpu'),observations)
                difference=lambda v:v['physical_signal'][1]-v['physical_signal'][0]
                near=[i for i,c in enumerate(cases) if c['distance_mm']==7 and c['speed_mm_per_second']==0]
                models.append({'seed':seed,'route':route,'timesteps':steps,'checkpoint':asset(run,cp),'checkpoint_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'checkpoint_config':config,'values':values,'zero_speed_steering_span':difference(values[near[-1]])-difference(values[near[0]]),'center_signal':values[near[8]]['physical_signal']})
    rule=[rule_action(o).tolist() for o in observations]
    output={'at':now(),'kind':'hypothetical-input-policy-query','source_version':preserve_source(run),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_definition':'먹이까지 1.5/3/7 mm, 방향 -40~40도(5도 간격), 몸 속력 0/6/12 mm/s. 회전 속력 0, 장애물 없음.','selection_note':'완료된 실패 사례를 보고 설계한 탐색적 검사입니다. 도착 문턱 1.2 mm보다 밖에서 멈추는 현상을 살펴보려고 가까운 거리도 포함했습니다.','cases':cases,'observations':observations.tolist(),'reference_rule_signals':rule,'models':models,'limitation':'가정한 관찰값을 저장된 모델에 넣은 출력입니다. 실제 이동 경로·방문 상태·성공률을 측정한 결과가 아닙니다. 신호 차이를 실제 회전 각도로 바꾸어 해석하지 않습니다.','source':'lab/policy_probe.py'}
    output['record_url']=asset(run,run/'policy-probe.json');atomic(run/'policy-probe.json',output);publish(run);return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');a=p.parse_args();result=probe(Path(a.run).resolve())
    for m in result['models']:print(m['seed'],m['route'],m['timesteps'],'angle response span',round(m['zero_speed_steering_span'],4),'center signal',m['center_signal'])
