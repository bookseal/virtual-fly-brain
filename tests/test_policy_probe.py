import math
import numpy as np
from lab.envs import FoodEnv
from lab.policy_probe import input_grid,query

def test_hypothetical_inputs_match_actual_environment_observation_encoding():
    cases,observations=input_grid();env=FoodEnv('2d',action_mode='normalized');env.reset(seed=11)
    env.pos=np.array([2.,-3.]);env.heading=.9
    assert len(cases)==153
    for case,observation in zip(cases,observations):
        angle=env.heading+math.radians(case['food_angle_degrees'])
        env.target=env.pos+case['distance_mm']*np.array([math.cos(angle),math.sin(angle)])
        env.distance=case['distance_mm'];env.v=case['speed_mm_per_second'];env.w=0
        np.testing.assert_allclose(observation,env._obs(),atol=1e-6)
    env.close()

def test_probe_distinguishes_unbounded_actor_mean_from_delivered_signal():
    import torch
    from stable_baselines3 import PPO
    env=FoodEnv('2d',action_mode='normalized')
    model=PPO('MlpPolicy',env,n_steps=8,batch_size=8,seed=11,device='cpu')
    with torch.no_grad():
        model.policy.action_net.weight.zero_();model.policy.action_net.bias.copy_(torch.tensor([2.,-2.]))
    _,observations=input_grid();row=query(model,observations[:1])[0]
    assert row['normalized_mean']==[2.,-2.]
    assert row['physical_signal']==[1.5,-.5]
    assert 0<row['expected_clipping_fraction']<1
    env.close()
