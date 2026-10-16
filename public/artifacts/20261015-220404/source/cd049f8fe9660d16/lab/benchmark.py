import argparse,concurrent.futures,json,time,os
from pathlib import Path
from .store import *
def worker(steps):
    import psutil,numpy as np
    from .envs import FoodEnv
    t=time.time();env=FoodEnv('3d');env.reset(seed=100);setup=time.time()-t;t=time.time()
    for _ in range(steps):env.step(np.array([1.,1.]))
    seconds=time.time()-t;rss=psutil.Process().memory_info().rss/2**20;env.close()
    return {'steps':steps,'seconds':seconds,'setup_seconds':setup,'rss_mb':rss}
def main():
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('--steps',type=int,default=12);a=p.parse_args();run=Path(a.run).resolve();rows=[]
    for n in [1,2,4]:
        t=time.time()
        with concurrent.futures.ProcessPoolExecutor(max_workers=n) as pool:result=list(pool.map(worker,[a.steps]*n))
        rate=sum(r['steps'] for r in result)/max(r['seconds'] for r in result)
        row={'workers':n,'decisions_per_second':rate,'projected_20k_hours':20000/rate/3600,'rss_total_mb':sum(r['rss_mb'] for r in result),'workers_data':result,'total_seconds':time.time()-t};rows.append(row)
        atomic(run/'benchmark.json',{'at':now(),'rendering':False,'rows':rows});event(run,'benchmark',f'3D {n}개 환경 속도 측정',**row);print(json.dumps(row),flush=True)
    best=max(rows,key=lambda r:r['decisions_per_second']);fallback=best['projected_20k_hours']*1.25>4
    decision={'at':now(),'best_workers':best['workers'],'activate_2d':fallback,'reason':'2만 행동과 평가 여유 25%를 포함한 예상 시간','projected_hours_including_evaluation':best['projected_20k_hours']*1.25,'measurement_steps_per_worker':a.steps,'short_benchmark':True}
    atomic(run/'backend-decision.json',decision);event(run,'decision','3D/2D 실행 방식 결정',**decision);publish(run)
if __name__=='__main__':main()
