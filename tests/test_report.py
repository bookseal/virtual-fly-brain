from lab.report import paired_seed_results


def test_replication_does_not_compare_unequal_budgets_or_missing_results():
    def row(seed,policy,steps,suite,score):
        return {'backend':'3d','task':'food-near','seed':seed,'policy':policy,'timesteps':steps,'evaluation_suite':suite,'success_rate':score,'record_url':f'{seed}/{policy}/{steps}', 'config':{'initialization':'random' if policy=='ppo' else 'behavior-cloning-from-rule'}}
    rows=[row(11,'ppo',10240,'same',.3),row(11,'bc-ppo',10240,'same',.8),row(29,'ppo',10240,'same',.4),row(29,'bc-ppo',20480,'same',.9),row(47,'ppo',10240,'old',.1),row(47,'bc-ppo',10240,'new',.9)]
    a,b=paired_seed_results(rows)
    assert a['completed_pairs']==1 and a['mean_difference_pp']==50
    assert a['pairs'][0]['seed']==11
    assert b['completed_pairs']==0 and b['mean_difference_pp'] is None
