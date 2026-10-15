"""Explicitly distinct 3D biomechanics and 2D differential-drive tasks.
Observation: body-relative target x/y, normalized distance, forward/turn speed,
nearest obstacle body-relative x/y and clearance (known coordinates, not smell).
"""
import math
import gymnasium as gym
import numpy as np

class FoodEnv(gym.Env):
    metadata={'render_modes':['rgb_array'],'render_fps':20}
    def __init__(self,backend='2d',task='food',curriculum='near',reward_mode='dense',max_steps=160,render_mode=None,action_mode='raw',physics_error_policy='raise'):
        self.backend,self.task,self.curriculum,self.reward_mode=backend,task,curriculum,reward_mode
        self.max_steps=max_steps;self.render_mode=render_mode;self.dt=.05
        if action_mode not in ('raw','normalized'):raise ValueError('Unknown action mode')
        self.action_mode=action_mode
        if physics_error_policy not in ('raise','terminate'):raise ValueError('Unknown physics error policy')
        self.physics_error_policy=physics_error_policy
        self.action_space=gym.spaces.Box(-1.,1.,(2,),dtype=np.float32) if action_mode=='normalized' else gym.spaces.Box(-.5,1.5,(2,),dtype=np.float32)
        self.observation_space=gym.spaces.Box(-np.inf,np.inf,(8,),dtype=np.float32)
        self.sim=None;self.camera=None
        if backend=='3d':self._build_3d()
    def _build_3d(self):
        from flygym_gymnasium import Fly,Camera
        from flygym_gymnasium.arena import FlatTerrain
        from flygym_gymnasium.examples.locomotion import HybridTurningController
        sensors=[f'{leg}{seg}' for leg in ['LF','LM','LH','RF','RM','RH'] for seg in ['Tibia','Tarsus1','Tarsus2','Tarsus3','Tarsus4','Tarsus5']]
        fly=Fly(enable_adhesion=True,contact_sensor_placements=sensors)
        arena=FlatTerrain()
        self.target_geom=arena.root_element.worldbody.add('geom',name='food_target',type='sphere',size=(.5,),pos=(8,0,.5),rgba=(.15,.75,.3,1),contype=0,conaffinity=0)
        self.obstacle_geom=None
        if self.task=='obstacles':self.obstacle_geom=arena.root_element.worldbody.add('geom',name='obstacle',type='cylinder',size=(1.2,1),pos=(5,0,1),rgba=(.7,.3,.2,1))
        cams=[]
        if self.render_mode:
            self.camera=Camera(attachment_point=arena.root_element.worldbody,camera_name='experiment_camera',window_size=(640,480),play_speed=1,fps=20,camera_parameters={'pos':(7,-14,22),'euler':(.55,0,0),'fovy':50})
            cams=[self.camera]
        self.sim=HybridTurningController(fly=fly,cameras=cams,arena=arena,timestep=1e-4,seed=0)
    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed);self.steps=0;self.collisions=0;self.flips=0;self.v=0.;self.w=0.
        radius=self.np_random.uniform(5,9) if self.curriculum=='near' else self.np_random.uniform(8,16)
        angle=self.np_random.uniform(-.7,.7) if self.curriculum=='near' else self.np_random.uniform(-math.pi,math.pi)
        self.target=np.array([radius*math.cos(angle),radius*math.sin(angle)])
        self.obstacle=self.target*.5 if self.task=='obstacles' else np.array([100.,100.])
        self.pos=np.zeros(2);self.heading=0.;self.last_info={}
        if self.sim:
            self.physics_seed=int(self.np_random.integers(0,2**31))
            raw,info=self.sim.reset(seed=self.physics_seed)
            self.sim.physics.bind(self.target_geom).pos[:2]=self.target
            if self.obstacle_geom:self.sim.physics.bind(self.obstacle_geom).pos[:2]=self.obstacle
            self._raw(raw)
        self.distance=float(np.linalg.norm(self.target-self.pos));self.path=[self.pos.tolist()];self.actions=[];self.policy_actions=[]
        return self._obs(),self._info(False,{})
    def _raw(self,raw):
        self.pos=np.array(raw['fly'][0][:2],dtype=float);o=raw['fly_orientation'];self.heading=math.atan2(o[1],o[0]);self.v=float(np.linalg.norm(raw['fly'][1][:2]))
    def _body(self,delta):
        c,s=math.cos(self.heading),math.sin(self.heading);return np.array([c*delta[0]+s*delta[1],-s*delta[0]+c*delta[1]])
    def _obs(self):
        rel=self._body(self.target-self.pos)/16
        ob=self._body(self.obstacle-self.pos)/16 if self.task=='obstacles' else np.zeros(2)
        clearance=max(0,np.linalg.norm(self.obstacle-self.pos)-1.2)/16 if self.task=='obstacles' else 1.
        return np.array([*rel,self.distance/16,self.v/20,self.w/8,*ob,min(clearance,2)],dtype=np.float32)
    def _info(self,success,terms):
        return {'success':bool(success),'distance':self.distance,'collisions':self.collisions,'flips':self.flips,'elapsed_sim_seconds':self.steps*self.dt,'reward_terms':terms,'position':self.pos.tolist(),'target':self.target.tolist(),'heading':self.heading}
    def step(self,action):
        policy_action=np.clip(np.asarray(action,dtype=float),self.action_space.low,self.action_space.high)
        action=policy_action+.5 if self.action_mode=='normalized' else policy_action
        before=self.distance;oldpos=self.pos.copy();oldheading=self.heading;flip=False;collision=False
        if self.sim:
            from dm_control.rl.control import PhysicsError
            try:
                for substep in range(500):
                    raw,_,term,trunc,info=self.sim.step(action);flip=flip or bool(info.get('flip',False))
                    if self.camera:self.sim.render()
                    if flip:break
            except PhysicsError as exc:
                if self.physics_error_policy=='raise':raise
                # The failed numerical state is not a biological fall and must
                # never enter the policy as a NaN observation or a success.
                self.steps+=1
                terms={'approach':0.,'arrival':0.,'time':-.025,'collision':0.,'flip':0.,'numerical_failure':-5.}
                self.path.append(self.pos.tolist());self.actions.append(action.tolist());self.policy_actions.append(policy_action.tolist())
                self.last_info=self._info(False,terms)
                self.last_info.update(numerical_failure=True,physics_error=str(exc),physics_seed=getattr(self,'physics_seed',None),physics_substep=substep,observation_is_last_valid=True,failure_actions=list(self.policy_actions))
                return self._obs(),sum(terms.values()),True,False,self.last_info
            self._raw(raw);self.w=math.atan2(math.sin(self.heading-oldheading),math.cos(self.heading-oldheading))/self.dt
            if self.task=='obstacles':
                obstacle_id=self.sim.physics.model.name2id('obstacle','geom')
                collision=any(obstacle_id in (c.geom1,c.geom2) for c in self.sim.physics.data.contact)
        else:
            # Kinematic proxy: no legs, inertia, contact solver or biological brain.
            self.v=8*float(np.mean(action));self.w=3.*float(action[1]-action[0]);self.heading+=self.w*self.dt
            self.pos+=self.v*self.dt*np.array([math.cos(self.heading),math.sin(self.heading)])
            if self.task=='obstacles' and np.linalg.norm(self.pos-self.obstacle)<1.8:collision=True;self.pos=oldpos
        self.steps+=1;self.distance=float(np.linalg.norm(self.target-self.pos));success=self.distance<1.2
        self.collisions+=int(collision);self.flips+=int(flip)
        terms={'approach':(before-self.distance) if self.reward_mode=='dense' else 0.,'arrival':20.*success,'time':-.025,'collision':-1.*collision,'flip':-5.*flip}
        self.path.append(self.pos.tolist());self.actions.append(action.tolist());self.policy_actions.append(policy_action.tolist());self.last_info=self._info(success,terms)
        return self._obs(),float(sum(terms.values())),bool(success or flip),bool(self.steps>=self.max_steps),self.last_info
    def render(self):
        if self.sim:
            return self.camera._frames[-1] if self.camera and self.camera._frames else None
        import cv2
        frame=np.full((480,640,3),247,np.uint8)
        def xy(p):return tuple(np.round(np.array([320,240])+np.array(p)*[14,-14]).astype(int))
        cv2.putText(frame,'2D SIMPLE MODEL / actual rollout',(18,26),cv2.FONT_HERSHEY_SIMPLEX,.55,(45,55,65),1)
        if self.task=='obstacles':cv2.circle(frame,xy(self.obstacle),25,(190,95,75),-1)
        cv2.circle(frame,xy(self.target),17,(65,175,95),-1)
        if len(self.path)>1:cv2.polylines(frame,[np.array([xy(p) for p in self.path])],False,(95,140,180),2)
        p=xy(self.pos);tip=xy(self.pos+np.array([math.cos(self.heading),math.sin(self.heading)]))
        cv2.circle(frame,p,7,(40,55,65),-1);cv2.arrowedLine(frame,p,tip,(210,85,50),2)
        cv2.putText(frame,f'step {self.steps} | distance {self.distance:.2f}',(18,458),cv2.FONT_HERSHEY_SIMPLEX,.55,(45,55,65),1)
        return frame
    def export_rng(self):return self.np_random.bit_generator.state
    def restore_rng(self,state):self.np_random.bit_generator.state=state
    def close(self):
        if self.sim:self.sim.close()

def rule_action(obs):
    angle=math.atan2(float(obs[1]),float(obs[0]));turn=np.clip(angle*1.2,-.9,.9)
    return np.clip(np.array([.8-turn,.8+turn]),-.5,1.5).astype(np.float32)

def env_options(config):
    return {k:v for k,v in config.items() if k in ['backend','task','curriculum','reward_mode','max_steps','action_mode','physics_error_policy']}

def teacher_action(env,obs):
    raw=rule_action(obs)
    return raw-.5 if env.action_mode=='normalized' else raw
