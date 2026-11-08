"""Bounded, local analysis tools. External text is never executed as instructions."""
import math
from datetime import datetime, timezone
import numpy as np
from ..schemas import AgentResult
from ..graph.analytics import build_graph, account_graph, metrics
from ..ml.prediction import predict

def result(agent,score,findings,ctx,details=None,confidence=.75,refs=None,uncertainty='Indicators are investigation leads; they do not establish fraud.'):
    return AgentResult(agent=agent,score=min(1,max(0,float(score))),confidence=confidence,findings=findings,
        references=refs or [ctx['transaction']['id']],provenance='persisted-transactions/as-of/'+ctx['transaction']['timestamp'],
        uncertainty=uncertainty,details=details or {}).model_dump()

def transaction(ctx, outputs):
    f=ctx['features']
    score=min(1,max(0,(f['amount_ratio']-1)/8)*.7+min(f['velocity_24h']/12,1)*.3)
    return result('transaction',score,[f"Amount is {f['amount_ratio']:.2f} times the past account mean; {f['velocity_24h']} prior transfers in 24h."],ctx,{'features':{k:v for k,v in f.items() if k not in ['timestamp','historical_label']}})

def behavioral(ctx,outputs):
    f=ctx['features']; prior=[r['amount'] for r in ctx['prior'] if r['account_id']==ctx['transaction']['account_id']]
    if len(prior)<5: return result('behavioral',0,['Insufficient account history for a stable behavioral baseline.'],ctx,{'baseline_count':len(prior)},confidence=.2)
    mean,std=float(np.mean(prior)),float(np.std(prior))
    z=(ctx['transaction']['amount']-mean)/max(std,1)
    score=min(1,max(0,z)/6)*.8+f['new_device']*.2
    return result('behavioral',score,[f'Amount deviation {z:.2f} standard deviations; new device indicator {f["new_device"]}.'],ctx,{'mean':mean,'std':std,'z_score':z,'baseline_count':len(prior)},refs=[r['id'] for r in ctx['prior'] if r['account_id']==ctx['transaction']['account_id']][-12:])

def account(ctx,outputs):
    t=ctx['transaction']; outgoing=[r for r in ctx['prior'] if r['account_id']==t['account_id']]
    incoming=[r for r in ctx['prior'] if r['beneficiary_id']==t['account_id']]
    in_value=sum(r['amount'] for r in incoming); out_value=sum(r['amount'] for r in outgoing)
    ratio=(out_value+t['amount'])/max(in_value,1)
    return result('account',min(.7,len({r['beneficiary_id'] for r in outgoing})/30)*ctx['features']['new_beneficiary'],
        [f'{len(incoming)} incoming and {len(outgoing)} outgoing historical transactions; {len(set(r["beneficiary_id"] for r in outgoing))} counterparties.'],ctx,
        {'incoming_amount':in_value,'outgoing_amount':out_value,'flow_ratio':ratio,'new_beneficiary':ctx['features']['new_beneficiary']})

def graph(ctx,outputs):
    t=ctx['transaction']; g=build_graph(ctx['prior']+[t]); p=account_graph(g); m=metrics(g)
    n='account:'+t['account_id']; b='account:'+t['beneficiary_id']
    related=[r for r in ctx['prior'] if r.get('device_id') and r.get('device_id')==t.get('device_id') and r['account_id']!=t['account_id']]
    peers=sorted({r['account_id'] for r in related})
    cycle=p.has_edge(b,n)
    score=min(1,len(peers)/8*.65+(.35 if cycle else 0))
    return result('graph',score,[f'{len(peers)} other accounts observed on the same device; reciprocal account link: {cycle}. A connection alone is not proof of misconduct.'],ctx,
        {'shared_device_accounts':peers,'reciprocal_link':cycle,'degree':m['degree'].get(n,0),'pagerank':m['pagerank'].get(n,0),'betweenness':m['betweenness'].get(n,0),
        'community':[c for c in m['communities'] if n in c],'relationships':[d for a,b,d in g.edges(data=True) if a==n][:25]},refs=[t['id']]+[r['id'] for r in related][-15:])

def ml(ctx,outputs):
    prediction=predict(ctx['features'],ctx['settings']['model'])
    return result('ml',prediction.get('fraud_probability') or 0,
        ['Calibrated supervised estimate and separate anomaly percentile.' if prediction['available'] else 'Model unavailable; uncertainty elevated.'],ctx,prediction,
        confidence=.75 if prediction['available'] else 0,uncertainty='Model estimates depend on training data and calibration; synthetic benchmark validity does not transfer to real banking.')

def pattern(ctx,outputs):
    t=ctx['transaction']
    # Only human-confirmed cases provided by the service, with review time before event time.
    matches=[c for c in ctx['verified_cases'] if c['account_id']==t['account_id'] or c['beneficiary_id']==t['beneficiary_id']]
    return result('pattern',min(.8,len(matches)/3),[f'{len(matches)} earlier human-confirmed cases share an account or beneficiary.'],ctx,
        {'matched_cases':matches},confidence=.6 if matches else .3,refs=[t['id']]+[c['transaction_id'] for c in matches])

def evidence(ctx,outputs):
    items=[]
    for name,output in outputs.items():
        for i,finding in enumerate(output['findings']):
            items.append({'id':f"{ctx['run_id']}:{name}:{i}",'type':name,'source':output['provenance'],
                'timestamp':ctx['transaction']['timestamp'],'collected_at':datetime.now(timezone.utc).isoformat(),
                'related_entity':ctx['transaction']['account_id'],'references':output['references'],
                'description':finding,'quality':output['confidence'],'provenance':{'agent':name,'method_version':'v1','transaction_ids':output['references']},
                'classification':'model_prediction' if name=='ml' else 'observed_indicator'})
    return result('evidence',0,[f'{len(items)} evidence items assembled from validated specialist outputs.'],ctx,{'items':items,'missing':[n for n in ['transaction','behavioral','account','graph','ml','pattern'] if n not in outputs]})

def risk(ctx,outputs):
    weights=ctx['settings']['weights']; breakdown={}
    for name,weight in weights.items():
        out=outputs.get(name)
        breakdown[name]={'weight':weight,'score':out['score'] if out else None,'contribution':round(100*weight*out['score'],3) if out else 0}
    priority=sum(v['contribution'] for v in breakdown.values())
    available=[outputs[n] for n in weights if n in outputs and outputs[n]['confidence']>0]
    quality=float(np.mean([o['confidence'] for o in available])) if available else 0
    scores=[o['score'] for o in available]
    contradictions=[]
    if scores and max(scores)-min(scores)>.55: contradictions.append('Specialist scores diverge by more than 0.55; inspect conflicting signals.')
    uncertainty=min(1,1-quality+(len(weights)-len(available))/len(weights)*.5)
    category='low'
    for label in ['medium','high','critical']:
        if priority>=ctx['settings']['thresholds'][label]: category=label
    return result('risk',priority/100,[f'Investigation priority {priority:.1f}/100 ({category}); this is not a fraud probability.'],ctx,
        {'priority':priority,'category':category,'breakdown':breakdown,'evidence_confidence':quality,'uncertainty':uncertainty,'contradictory_evidence':contradictions},confidence=quality)

def investigation(ctx,outputs):
    return result('investigation',outputs['risk']['score'],['Structured investigation assembled; human review required.'],ctx,
        {'timeline':sorted(outputs['evidence']['details']['items'],key=lambda i:i['timestamp']),
        'questions':['Was this transaction authorized?','Can the observed device relationship be independently verified?'],
        'recommendations':['Review referenced transaction records and obtain independent corroboration.','Record an authorized human outcome; no banking action is executed.'],
        'missing_information':['Independent customer authorization confirmation','External corroboration of device identity']})

def compliance(ctx,outputs):
    missing=outputs['evidence']['details']['missing']
    return result('compliance',0,['Human approval required for consequential decisions. No funds movement, restriction, blocking or external reporting is supported.'],ctx,
        {'policy_version':ctx['settings']['policy_version'],'human_review_required':True,'missing_agents':missing,
        'retention_days':ctx['settings']['retention_days'],'policy_checks_passed':not bool(missing),
        'limitations':'Configured policy checks do not certify regulatory compliance.'})

def reporting(ctx,outputs):
    return result('reporting',outputs['risk']['score'],['Evidence-grounded report ready for supervisor review.'],ctx,
        {'executive_summary':outputs['risk']['findings'][0], 'transaction':ctx['transaction'],
        'risk_assessment':outputs['risk']['details'], 'evidence':outputs['evidence']['details']['items'],
        'investigation':outputs['investigation']['details'], 'policy':outputs['compliance']['details'],
        'limitations':['All predictions and observed indicators require human corroboration.','Graph links are investigation leads, not criminal associations.',
        'No automatic customer adverse action is supported.','Synthetic records and simulated historical labels are development data.'],
        'agent_findings':{k:v for k,v in outputs.items() if k!='reporting'}})

SPECIALISTS={'transaction':transaction,'behavioral':behavioral,'account':account,'graph':graph,'ml':ml,'pattern':pattern,
    'evidence':evidence,'risk':risk,'investigation':investigation,'compliance':compliance,'reporting':reporting}
