"""A focused follow-up shares its task's rubric budget, not four new decisions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.artifacts import atomic_json
from pipeline.author.quality import production_problems
from pipeline.harden import acceptance
from pipeline.measurement import profile, task_profile
from pipeline.tests.test_production import synthetic_bundle


def counts(successes):
    return {'kind':'objective', 'passed':successes, 'failed':10-successes, 'gated_out':0}


def steps(rates=(5,5,5,5,10,1,5)):
    return {'initial':{'checks':{f'c{i}':counts(n) for i,n in enumerate(rates[:6])}},
            'followup':{'checks':{'c6':counts(rates[6])}}}


class TaskRubricBudget(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.bundle=Path(self.tmp.name)/'bundle'
        checks=[{'id':cid,'kind':'objective','step':step,'weight':1}
                for step,data in steps().items() for cid in data['checks']]
        # The follow-up revisits the first professional decision. It must not
        # pretend to create another independent core decision.
        decisions=[{'id':f'd{i}','checks':[f'c{i}']+(['c6'] if i==0 else [])} for i in range(6)]
        atomic_json(self.bundle/'tests/checks.json',{'checks':checks})
        atomic_json(self.bundle/'authoring/spec.json',{'quality':{'decisions':decisions}})

    # The build-time pilot (`orchestrate.pilot_selection`) was removed with the
    # in-build difficulty loop (2026-09-25): difficulty is measured once, for
    # the whole batch, by the calibration screen. Bands remain diagnosis.

    def test_transition_check_passes_final_bands_and_hardening_selection(self):
        rates=(5,5,5,5,8,1,5)
        self.assertEqual(task_profile({s:profile(d['checks']) for s,d in steps(rates).items()})['bands'],
                         {'core':5,'transition':1,'stretch':1})

        def measured(rates):
            return {'ok':True,'errors':[],'by_model':{m:{'protocol':'native','effort':'xhigh','limits':{},
                'pass_at_1':min(rates)/10,'episodes_valid':10,
                'capability_difficulty':{'capability_adjusted_pass_at_1':min(rates)/10},
                'steps':{s:profile(d['checks']) for s,d in steps(rates).items()}} for m in ['one','two']}}
        before=measured((10,)*7);after=measured(rates)
        self.assertTrue(acceptance(before,after,True,True,[])['accept'])
        # Bands diagnose; they no longer decide (POLICY.md). What decides is
        # pass@1 falling on every model.
        after['by_model']['two']=measured((10,)*7)['by_model']['two']
        self.assertFalse(acceptance(before,after,True,True,[])['accept'])

    def test_repeated_check_or_decision_cannot_inflate_core(self):
        repeated=steps();repeated['followup']['checks']['c0']=counts(5)
        with self.assertRaisesRegex(ValueError,'multiple steps'):task_profile(repeated)

    def test_hardening_compares_the_task_mix_without_pooling_models(self):
        def report(rates):
            return {'ok':True,'errors':[],'by_model':{m:{'protocol':'native','effort':'xhigh','limits':{},
                'pass_at_1':min(rates)/10,'episodes_valid':10,
                'capability_difficulty':{'capability_adjusted_pass_at_1':min(rates)/10},
                'steps':{s:profile(d['checks']) for s,d in steps(rates).items()}} for m in ['one','two']}}
        before=report((10,)*7);after=report((5,5,5,5,10,1,5))
        self.assertTrue(acceptance(before,after,True,True,[])['accept'])
        after['by_model']['two']=report((10,)*7)['by_model']['two']
        self.assertFalse(acceptance(before,after,True,True,[])['accept'])

    def test_author_budget_is_whole_task_but_each_step_needs_substantive_weight(self):
        bundle=synthetic_bundle(Path(self.tmp.name)/'authored',two_steps=True)
        spec=json.loads((bundle/'authoring/spec.json').read_text())
        objectives=[c for c in spec['checks'] if c['kind']=='objective']
        for c in objectives:c['band']='core'
        extra=copy.deepcopy(objectives[2]);extra.update(id='stretch_analysis',band='stretch')
        extra['actual']['path']='stretch_analysis'
        spec['checks'].append(extra)
        schema=spec['outputs'][0]['schema'];schema['properties']['stretch_analysis']={'type':'integer'};schema['required'].append('stretch_analysis')
        semantic=[c['id'] for c in spec['checks'] if c['kind']=='objective']
        spec['quality']={'semantic_checks':semantic,'decisions':[{'id':f'd{i}','question':'A decision','shortcut':'A wrong shortcut',
            'sources':['tickets.csv'],'checks':[cid]} for i,cid in enumerate(semantic)]}
        # Other semantic/citation controls intentionally remain unfulfilled in
        # this budget fixture; this test makes no claim of release validity.
        # v2 (user, 2026-10-02): band, decision and weight-share rules are still
        # REPORTED but are advisories -- none may block or start a repair.
        from pipeline.advisory import classify
        errors=production_problems(spec,bundle)
        shape=[e for e in errors if 'task: require' in e or 'four distinct core' in e or '70% substantive' in e]
        self.assertTrue(all(classify(e) for e in shape),shape)
        objectives[-1]['band']='floor'
        errors=production_problems(spec,bundle)
        self.assertTrue(any('02-revision: each scored step' in e for e in errors),errors)
        self.assertTrue(all(classify(e) for e in errors if '02-revision: each scored step' in e))
