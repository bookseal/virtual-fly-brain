"""Isolated CPU walking smoke test; not a policy or equal-model benchmark.

Run modern with the separate FlyGym 2.1 environment and legacy with .venv.
Both use 100 microsecond physics steps and constant descending signals.
"""
import argparse,hashlib,importlib.metadata,json,platform,time
from pathlib import Path
import numpy as np
from .store import atomic,now,asset,preserve_source

def modern(seconds,repeats,video_path):
    from flygym import Simulation
    from flygym.anatomy import BodySegment,ContactBodiesPreset
    from flygym.compose import FlatGroundWorld
    from flygym_demo.complex_terrain import HybridTurningController,HybridControllerObservation,LocomotionAction,PreprogrammedSteps,apply_locomotion_action,make_locomotion_fly
    from flygym.utils.math import Rotation3D
    setup=time.perf_counter();fly=make_locomotion_fly(name='compatibility',add_adhesion=True,colorize=True)
    camera=fly.add_tracking_camera(name='probe_camera',pos_offset=(-.5,-7.5,5),rotation=Rotation3D('euler',(.8,0,0)),fovy=50.)
    world=FlatGroundWorld();world.add_fly(fly,[0,0,.8],Rotation3D('quat',[1,0,0,0]),bodysegs_with_ground_contact=ContactBodiesPreset.TIBIA_TARSUS_ONLY,add_ground_contact_sensors=False)
    sim=Simulation(world,timestep=1e-4);steps=PreprogrammedSteps();order=fly.get_actuated_jointdofs_order('position')
    controller=HybridTurningController(timestep=sim.timestep,preprogrammed_steps=steps,output_dof_order=order)
    idx=fly.get_bodysegs_order().index(BodySegment('c_thorax'));setup_seconds=time.perf_counter()-setup
    def reset(seed):
        sim.reset();controller.reset(seed=seed);apply_locomotion_action(sim,fly.name,LocomotionAction(joint_angles=steps.default_pose_by_dof_order(order),adhesion_onoff=np.ones(6,dtype=bool)));sim.warmup()
    def rollout(seed,duration,render=False):
        reset(seed);path=[sim.get_body_positions(fly.name)[idx].tolist()];start=time.perf_counter();count=round(duration/sim.timestep)
        for i in range(count):
            observation=HybridControllerObservation.from_sim(sim,fly.name)
            action=controller.step(np.array([.8,.8]),observation);apply_locomotion_action(sim,fly.name,action);sim.step()
            if render:sim.render_as_needed_with_profile()
            if (i+1)%500==0:path.append(sim.get_body_positions(fly.name)[idx].tolist())
        elapsed=time.perf_counter()-start
        if not np.isfinite(path).all():raise RuntimeError('Nonfinite modern path')
        return {'seed':seed,'simulation_seconds':duration,'wall_seconds':elapsed,'physics_steps':count,'equivalent_50ms_decisions_per_second':duration/.05/elapsed,'path_xyz':path,'rendered':render}
    try:
        # First execution includes cold controller/JIT initialization. Keep it
        # as evidence but exclude it from the warmed measurement median.
        cold=rollout(0,.1);rows=[rollout(seed,seconds) for seed in range(repeats)]
        if video_path:
            sim.set_renderer([camera],camera_res=(480,640),playback_speed=1.,output_fps=20)
            rendered=rollout(0,2.,True);sim.renderer.save_video(video_path)
        else:rendered=None
        return setup_seconds,cold,rows,rendered
    finally:sim.close()

def legacy(seconds,repeats):
    from .envs import FoodEnv
    setup=time.perf_counter();env=FoodEnv('3d');setup_seconds=time.perf_counter()-setup
    def rollout(seed,duration):
        env.reset(seed=seed);path=[env.sim.get_observation()['fly'][0].tolist()];start=time.perf_counter();count=round(duration/1e-4)
        for i in range(count):
            raw,_,_,_,_=env.sim.step(np.array([.8,.8]))
            if (i+1)%500==0:path.append(raw['fly'][0].tolist())
        elapsed=time.perf_counter()-start
        if not all(np.isfinite(p).all() for p in path):raise RuntimeError('Nonfinite legacy path')
        return {'seed':seed,'simulation_seconds':duration,'wall_seconds':elapsed,'physics_steps':count,'equivalent_50ms_decisions_per_second':duration/.05/elapsed,'path_xyz':path,'rendered':False}
    try:return setup_seconds,rollout(0,.1),[rollout(seed,seconds) for seed in range(repeats)],None
    finally:env.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('--flavor',choices=['modern','legacy'],required=True);ap.add_argument('--seconds',type=float,default=1.);ap.add_argument('--repeats',type=int,default=3);ap.add_argument('--video',action='store_true');a=ap.parse_args()
    run=Path(a.run).resolve();dest=run/'compatibility/flygym2';dest.mkdir(parents=True,exist_ok=True);(run/'media').mkdir(exist_ok=True)
    dependencies=dest/('requirements.lock.txt' if a.flavor=='modern' else 'legacy-requirements.lock.txt')
    if not dependencies.exists():dependencies.write_text('\n'.join(sorted(f'{d.metadata["Name"]}=={d.version}' for d in importlib.metadata.distributions()))+'\n')
    video=run/'media/flygym-2.1-walking-probe.mp4' if a.video else None
    started=now();result={'status':'running','started_at':started,'flavor':a.flavor,'purpose':'CPU API compatibility and fixed-command walking; not learned behavior','source':'https://github.com/NeLy-EPFL/flygym/blob/v2.1.0/tutorials/4d_turning_controller.ipynb','probe_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'architecture':platform.machine(),'python':platform.python_version(),'versions':{p:importlib.metadata.version(p) for p in (['flygym','mujoco','numpy'] if a.flavor=='modern' else ['flygym-gymnasium','mujoco','numpy'])},'command':f'python -m lab.compatibility_probe runs/{run.name} --flavor {a.flavor} --seconds {a.seconds} --repeats {a.repeats}'+(' --video' if a.video else ''),'limitation':'몸·제어기 구현과 초기 안정화 방식이 다릅니다. 같은 학습 과제의 속도 향상 비율로 해석하지 않습니다. 주 실험 2 worker가 실행 중인 Mac에서 측정했습니다.'}
    result['source_version']=preserve_source(run)
    result['requirements']=asset(run,dest/('requirements.lock.txt' if a.flavor=='modern' else 'legacy-requirements.lock.txt'))
    record=dest/(a.flavor+'.json');result['record_url']=asset(run,record);atomic(record,result)
    try:
        setup,cold,rows,rendered=modern(a.seconds,a.repeats,video) if a.flavor=='modern' else legacy(a.seconds,a.repeats)
        result.update(status='completed',completed_at=now(),setup_seconds=setup,cold_probe=cold,rows=rows,median_decisions_per_second=float(np.median([r['equivalent_50ms_decisions_per_second'] for r in rows])),rendered_probe=rendered,video=asset(run,video) if video and video.exists() else None)
    except Exception as exc:
        result.update(status='failed',completed_at=now(),error=repr(exc));raise
    finally:atomic(record,result)
    print(json.dumps({k:result.get(k) for k in ['status','flavor','versions','setup_seconds','median_decisions_per_second','video']},ensure_ascii=False))
if __name__=='__main__':main()
