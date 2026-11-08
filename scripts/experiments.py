"""Actual offline ablations. Results are operational proxies, not investigator studies."""
import argparse,copy,json,sys
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import numpy as np
from backend.app.ml.features import engineer
from backend.app.ml.prediction import predict
from backend.app.ml.training import evaluate
from backend.app.agents.supervisor import Supervisor
from backend.app.config import DEFAULT_SETTINGS,ROOT

def run(count=30):
    data=pd.read_csv(ROOT/'data/synthetic/transactions.csv');features=engineer(data)
    # Use only the later test period; deterministic spread, no label-based selection.
    test=features.iloc[int(len(features)*.8):]
    rng=np.random.default_rng(42)
    selected=test.iloc[sorted(rng.choice(len(test),min(count,len(test)),replace=False))]
    scenarios={'single_model':None,'ml_plus_graph':('transaction','behavioral','account','pattern'), 'full':(),
        'without_behavioral':('behavioral',),'without_graph':('graph',),'without_ml':('ml',),
        'without_evidence':('evidence',),'without_supervisor_aggregation':('risk',)}
    results={}
    for name,disabled in scenarios.items():
        priorities=[];labels=[];durations=[];coverage=[];failures=0
        for f in selected.to_dict('records'):
            t=data[data.id==f['id']].iloc[0].to_dict();prior=data[data.timestamp<t['timestamp']].to_dict('records')
            began=perf_counter()
            if disabled is None:
                p=predict(f);score=p['fraud_probability'] or 0;ev=0
            else:
                context={'transaction':t,'features':f,'prior':prior,'settings':copy.deepcopy(DEFAULT_SETTINGS),'verified_cases':[],'run_id':'offline-'+t['id']}
                state=Supervisor().run(context,disabled=disabled)
                risk=state['results'].get('risk')
                score=risk['score'] if risk else 0
                ev=len(state['results'].get('evidence',{}).get('details',{}).get('items',[]))
                failures+=int(state['phase']=='incomplete')
            priorities.append(score);labels.append(int(t['historical_label']));durations.append((perf_counter()-began)*1000);coverage.append(ev)
        results[name]={'ranking_metrics':evaluate(np.array(labels),np.array(priorities)),
            'score_type':'calibrated_supervised_probability' if disabled is None else 'uncalibrated_investigation_priority',
            'mean_duration_ms':float(np.mean(durations)),'mean_evidence_items':float(np.mean(coverage)),
            'incomplete_workflows':failures,'sampled_test_records':len(labels),'alert_volume_at_research_threshold':int(sum(s>=.3 for s in priorities))}
    report={'seed':42,'results':results,'limitations':['Synthetic, sampled offline evaluation only.','Ablations intentionally omit agents and can yield incomplete workflows.',
        'Evidence count is a completeness proxy, not evidence correctness.','Human effort has not been measured; requires a prospective investigator study.',
        'Priority threshold and 0.5 classification threshold are arbitrary research settings.','Ablation scores retain original weights without renormalization.']}
    path=ROOT/'models/experiments.json';path.write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=30);args=parser.parse_args();print(json.dumps(run(args.count),indent=2))
