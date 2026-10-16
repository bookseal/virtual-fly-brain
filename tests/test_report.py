from lab.report import paired_seed_results, evaluation_contract


def test_replication_does_not_compare_unequal_budgets_or_missing_results():
    def row(seed,policy,steps,suite,score):
        return {'backend':'3d','task':'food-near','seed':seed,'policy':policy,'timesteps':steps,'evaluation_suite':suite,'success_rate':score,'record_url':f'{seed}/{policy}/{steps}', 'config':{'initialization':'random' if policy=='ppo' else 'behavior-cloning-from-rule'}}
    rows=[row(11,'ppo',10240,'same',.3),row(11,'bc-ppo',10240,'same',.8),row(29,'ppo',10240,'same',.4),row(29,'bc-ppo',20480,'same',.9),row(47,'ppo',10240,'old',.1),row(47,'bc-ppo',10240,'new',.9)]
    a,b=paired_seed_results(rows)
    assert a['completed_pairs']==1 and a['mean_difference_pp']==50
    assert a['pairs'][0]['seed']==11
    assert b['completed_pairs']==0 and b['mean_difference_pp'] is None


def test_same_seeds_and_budget_do_not_override_changed_evaluation_rules():
    from copy import deepcopy
    a={'backend':'3d','task':'food-near','seed':11,'policy':'ppo',
       'timesteps':10240,'evaluation_suite':'same','success_rate':.2,
       'record_url':'a','config':{'initialization':'random'}}
    b=deepcopy(a);b.update(policy='bc-ppo',record_url='b',success_rate=1.)
    b['config']['initialization']='behavior-cloning-from-rule'
    assert paired_seed_results([a,b])[0]['completed_pairs']==1
    for key,value in [('physics_error_policy','terminate'),('reward_mode','sparse'),
                      ('max_steps',120),('action_mode','normalized'),
                      ('curriculum','wide'),('environment_version','v2')]:
        changed=deepcopy(b);changed['config'][key]=value
        assert paired_seed_results([a,changed])[0]['completed_pairs']==0,key


def test_explicit_historical_defaults_match_missing_defaults():
    row={'backend':'3d','task':'food-near','evaluation_suite':'same','config':{}}
    explicit={**row,'config':{'physics_error_policy':'raise','action_mode':'raw',
                            'max_steps':160,'reward_mode':'dense','curriculum':'near'}}
    assert evaluation_contract(row)==evaluation_contract(explicit)


def test_valid_pairs_with_different_protocols_are_not_pooled():
    rows=[]
    for seed,physics in [(11,'raise'),(29,'terminate')]:
        for policy,initial in [('ppo','random'),('bc-ppo','behavior-cloning-from-rule')]:
            rows.append({'backend':'3d','task':'food-near','seed':seed,'policy':policy,
                'timesteps':10240,'evaluation_suite':'same','success_rate':.5,
                'record_url':f'{seed}/{policy}','config':{'initialization':initial,
                'physics_error_policy':physics}})
    result=paired_seed_results(rows)[0]
    assert result['completed_pairs']==2 and result['evaluation_protocol_count']==2
    assert result['mean_difference_pp'] is None
