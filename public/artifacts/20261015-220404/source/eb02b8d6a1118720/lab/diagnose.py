"""Measured action calibration. No learning or synthetic performance claims."""
import argparse,time
import numpy as np
from .envs import FoodEnv
from .store import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();run=Path(a.run).resolve()
    rows=[]
    for label,action in [('near-zero',[0.,0.]),('old-ppo-mean',[.065,-.224]),('forward',[.8,.8]),('left',[.4,1.2]),('right',[1.2,.4])]:
        start=time.time();env=FoodEnv(backend='3d',max_steps=40,render_mode='rgb_array');obs,info=env.reset(seed=110001);frames=[]
        try:
            for i in range(40):
                obs,reward,term,trunc,info=env.step(action)
                frame=env.render()
                if frame is not None:frames.append(frame.copy())
                if term or trunc:break
            import imageio.v2 as imageio
            video=run/'media'/f'calibration-{label}.mp4';imageio.mimsave(video,frames,fps=20,macro_block_size=1)
            row={'label':label,'action':action,'seed':110001,'steps':i+1,'position':env.pos.tolist(),'heading':env.heading,'distance':env.distance,'path':env.path,'target':env.target.tolist(),'video':asset(run,video),'seconds':time.time()-start,'measured_at':now()};rows.append(row)
            atomic(run/'diagnostics.json',{'kind':'3d-action-calibration','status':'running','rows':rows,'note':'고정 신호의 실제 동작 보정. 학습 성능 평가가 아닙니다.'});publish(run)
            event(run,'diagnosis',f'고정 행동 보정: {label}',measurement=row)
        finally:env.close()
    atomic(run/'diagnostics.json',{'kind':'3d-action-calibration','status':'completed','rows':rows,'note':'고정 신호의 실제 동작 보정. 학습 성능 평가가 아닙니다.'});publish(run)
if __name__=='__main__':main()
