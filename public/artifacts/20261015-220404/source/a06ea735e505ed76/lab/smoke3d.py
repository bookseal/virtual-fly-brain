import argparse,time,json
from pathlib import Path
import numpy as np,psutil,imageio.v2 as imageio
from .envs import FoodEnv
from .store import *
def main():
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('--steps',type=int,default=40);a=p.parse_args();run=Path(a.run).resolve();t=time.time()
    event(run,'command','3D 몸의 첫 실제 실행',command=f'.venv/bin/python -m lab.smoke3d {run} --steps {a.steps}',command_ko='실제 3D 초파리 몸으로 두 하강 신호를 보내고 움직임과 속도를 기록합니다.')
    env=FoodEnv('3d',render_mode='rgb_array');obs,info=env.reset(seed=101);start=time.time();frames=[]
    for i in range(a.steps):
        obs,r,term,trunc,info=env.step(np.array([1.,1.]));frame=env.render()
        if frame is not None:frames.append(frame.copy())
        if term or trunc:break
    elapsed=time.time()-start;path=run/'media/first-3d-walk.mp4'
    if frames:imageio.mimsave(path,frames,fps=20,macro_block_size=1)
    result={'backend':'3d','physics_steps':(i+1)*500,'decisions':i+1,'wall_seconds':elapsed,'decisions_per_second':(i+1)/elapsed,'projected_20k_hours':20000*elapsed/(i+1)/3600,'rss_mb':psutil.Process().memory_info().rss/1024**2,'info':info,'path':env.path,'video':asset(run,path) if frames else None,'at':now()}
    atomic(run/'smoke3d.json',result);event(run,'result','3D 첫 실행 결과',**result);env.close();print(json.dumps(result))
if __name__=='__main__':main()
