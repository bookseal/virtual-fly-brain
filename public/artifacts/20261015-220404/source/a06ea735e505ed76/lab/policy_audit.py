from pathlib import Path
import json,numpy as np,torch
from stable_baselines3 import PPO
from .store import atomic,now,asset

def audit(run):
    r=Path(run);torch.set_num_threads(1)
    x=[];y=[]
    for seed in range(210000,210020):
     with np.load(r/'demonstrations'/f'{seed}.npz') as z:x.extend(z['observations']);y.extend(z['actions'])
    x=torch.tensor(np.array(x),dtype=torch.float32);y=np.array(y);rows=[]
    for seed in [11,29]:
     for route in ['ppo','bc-ppo']:
      for steps in [0,2048,8192,10240]:
       p=r/'checkpoints'/f'3d-near-{route}-seed{seed}'/f'step-{steps:09d}.zip'
       if not p.exists():continue
       model=PPO.load(p,device='cpu')
       with torch.no_grad():
        dist=model.policy.get_distribution(x).distribution;means=dist.mean.numpy();std=dist.stddev.numpy();clipping=(dist.cdf(torch.full_like(dist.mean,-1))+(1-dist.cdf(torch.ones_like(dist.mean)))).mean().item()
       row=dict(seed=seed,route=route,timesteps=steps,checkpoint=asset(r,p),unclipped_mean_signal=(means+.5).mean(0).tolist(),clipped_mean_signal=(np.clip(means,-1,1)+.5).mean(0).tolist(),std=std.mean(0).tolist(),teacher_mse=float(np.mean((means-y)**2)),expected_clipped_fraction=clipping)
       rows.append(row)
    atomic(r/'policy-audit.json',{'at':now(),'kind':'fixed-demonstration-observation-audit','observations':len(x),'validation_seeds':list(range(210000,210020)),'limitation':'시범 관찰값에서 정책 출력을 검사합니다. 실제 정책이 방문하는 상태 분포나 성공률을 대신하지 않습니다.','rows':rows})
    return rows

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("run");a=p.parse_args();print("policy checkpoints audited:",len(audit(Path(a.run).resolve())))
