import argparse,time
from pathlib import Path
from .store import *
from .learning import train,evaluate

def main():
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('--workers',type=int,default=4);a=p.parse_args();run=Path(a.run).resolve();config=read(run/'configs/3d-food-near-seed11.json')
    baseline={}
    previous=read(run/'baseline-progress.json',{})
    for policy in ['random','rule']:
        baseline[policy]=read(ROOT/'site'/previous[policy]) if policy in previous else evaluate(run,config,policy,workers=a.workers)
        atomic(run/'baseline-progress.json',{k:v['record_url'] for k,v in baseline.items()})
    initial=train(run,config,0,a.workers)
    baseline['untrained']=evaluate(run,config,'untrained',initial['checkpoint'],workers=a.workers)
    atomic(run/'baselines.json',{k:v['record_url'] for k,v in baseline.items()})
    event(run,'milestone','3D 학습 전 기준선 확보',results={k:v['success_rate'] for k,v in baseline.items()})
if __name__=='__main__':main()
