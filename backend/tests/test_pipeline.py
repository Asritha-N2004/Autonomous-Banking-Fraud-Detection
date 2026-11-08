import copy
import pandas as pd
import pytest
from sqlalchemy import select
from backend.app.ml.data import generate
from backend.app.ml.features import engineer
from backend.app.ml.prediction import predict
from backend.app.graph.analytics import build_graph,metrics,neighborhood
from backend.app.schemas import TransactionInput
from backend.app.config import DEFAULT_SETTINGS
from backend.app.agents.supervisor import Supervisor
from backend.app.agents.specialists import SPECIALISTS
from backend.app.database import AuditLog,Transaction,Investigation

def seed(client,n=200):
    data=generate(n)
    response=client.post('/api/transactions/batch',json=data.to_dict('records'))
    assert response.status_code==201,response.text
    return data

def test_seed_reproducible_and_synthetic():
    assert generate(20).equals(generate(20))
    assert generate(20).synthetic.all()

def test_validation_and_duplicate(admin):
    row=generate(1).iloc[0].to_dict(); row['amount']=-1
    assert admin.post('/api/transactions',json=row).status_code==422
    row=generate(1).iloc[0].to_dict(); row['timestamp']='2025-01-01T00:00:00'
    assert admin.post('/api/transactions',json=row).status_code==422
    seed(admin,2)
    assert admin.post('/api/transactions',json=generate(1).iloc[0].to_dict()).status_code==409

def test_features_no_future_or_label_leakage():
    data=generate(40)
    original=engineer(data)
    changed=data.copy(); changed.loc[20:,'amount']=99999999; changed['historical_label']=1-changed['historical_label']
    current=engineer(changed)
    cols=['prior_mean','amount_ratio','velocity_24h','account_degree']
    pd.testing.assert_frame_equal(original.loc[:19,cols],current.loc[:19,cols])
    assert engineer(data).iloc[0].prior_count==0

def test_equal_timestamp_not_used_as_history():
    data=generate(3); data['account_id']='SYN-A000'; data['timestamp']=data.iloc[0].timestamp
    assert engineer(data).prior_count.tolist()==[0,0,0]

def test_graph_evidence_and_time():
    rows=generate(25).to_dict('records'); g=build_graph(rows,rows[4]['timestamp'])
    assert all(d['evidence_reference'] in {r['id'] for r in rows[:5]} for *_,d in g.edges(data=True))
    m=metrics(g); assert m['nodes']>0 and m['pagerank']
    n=neighborhood(g,'account:'+rows[0]['account_id']); assert n['nodes'] and n['edges']

def test_authentication_roles_and_logout(client):
    assert client.get('/api/transactions').status_code==401
    assert client.post('/api/auth/login',json={'username':'admin','password':'wrong'}).status_code==401
    client.post('/api/auth/login',json={'username':'analyst','password':'Synthetic-Test-Password!'})
    assert client.get('/api/analytics/dashboard').status_code==200
    assert client.patch('/api/settings',json={}).status_code==403
    assert client.post('/api/fraud/analyze',json={'transaction_id':'missing'}).status_code==403
    client.post('/api/auth/logout'); assert client.get('/api/auth/me').status_code==401

def test_end_to_end_evidence_human_review_exports(admin):
    data=seed(admin)
    tx=data.sort_values('amount',ascending=False).iloc[0].id
    response=admin.post('/api/fraud/analyze',json={'transaction_id':tx})
    assert response.status_code==200,response.text
    result=response.json(); case_id=result['case_id']; run_id=result['run_id']
    case=admin.get('/api/investigations/'+case_id).json()
    assert len(case['report']['agent_findings'])==10
    assert case['report']['evidence']
    assert case['report']['policy']['human_review_required']
    assert all(e['references'] and e['provenance'] for e in case['report']['evidence'])
    logs=admin.get('/api/agents/logs/'+run_id).json()['items']
    assert len(logs)==11 and all(l['payload']['status']=='completed' for l in logs)
    assert admin.get('/api/graph/investigation/'+case_id).json()['nodes']
    assert admin.post(f'/api/investigations/{case_id}/notes',json={'text':'Synthetic test note'}).status_code==200
    for fmt in ['json','csv','pdf']:
        export=admin.get(f'/api/investigations/{case_id}/report?format={fmt}')
        assert export.status_code==200,export.text[:100]
        if fmt=='pdf': assert export.content.startswith(b'%PDF')
    outcome=admin.post(f'/api/investigations/{case_id}/review',json={'outcome':'false_positive','rationale':'Synthetic test; independently verified authorization.','decision':'approve_recommendation'})
    assert outcome.json()['status']=='closed'
    assert outcome.json()['banking_actions_executed'] is False
    assert outcome.json()['review']['supporting_evidence']
    with admin.db_factory() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action=='human_review')).user_id=='ADMIN'
        assert db.get(Transaction,tx).historical_label==int(data[data.id==tx].iloc[0].historical_label)

def test_assignment_isolation(admin):
    data=seed(admin,30)
    case_id=admin.post('/api/investigations',json={'transaction_id':data.iloc[-1].id}).json()['case_id']
    admin.post('/api/auth/logout')
    admin.post('/api/auth/login',json={'username':'fraud_investigator','password':'Synthetic-Test-Password!'})
    assert admin.get('/api/investigations/'+case_id).status_code==403
    assert admin.get('/api/investigations').json()['total']==0
    assert admin.get('/api/evidence').json()['total']==0
    assert admin.get('/api/transactions').status_code==403

def test_settings_validation(admin):
    body=copy.deepcopy(DEFAULT_SETTINGS); body['weights']['ml']=5
    assert admin.patch('/api/settings',json=body).status_code==422
    body=copy.deepcopy(DEFAULT_SETTINGS); body['thresholds']['high']=20
    assert admin.patch('/api/settings',json=body).status_code==422
    assert admin.patch('/api/settings',json=DEFAULT_SETTINGS).status_code==200

def test_supervisor_retry_and_provenance(monkeypatch):
    data=generate(30); t=data.iloc[-1].to_dict(); f=engineer(data).iloc[-1].to_dict()
    ctx={'transaction':t,'features':f,'prior':data.iloc[:-1].to_dict('records'),'verified_cases':[],'settings':copy.deepcopy(DEFAULT_SETTINGS),'run_id':'synthetic-test'}
    original=SPECIALISTS['account']; calls=[]
    def fail_once(ctx,outputs):
        calls.append(1)
        if len(calls)==1: raise ValueError('Synthetic temporary failure')
        return original(ctx,outputs)
    monkeypatch.setitem(SPECIALISTS,'account',fail_once)
    result=Supervisor().run(ctx)
    assert result['phase']=='human_review_checkpoint'
    assert next(l for l in result['logs'] if l['agent']=='account')['attempts']==2
    def fabricated(ctx,outputs):
        out=original(ctx,outputs); out['references']=['FABRICATED']; return out
    monkeypatch.setitem(SPECIALISTS,'account',fabricated)
    result=Supervisor().run(ctx)
    assert 'account' in result['errors']
    assert 'account' in result['results']['compliance']['details']['missing_agents']

def test_ml_prediction_is_separate_from_anomaly():
    data=generate(30); data.loc[29,'timestamp']='2025-03-01T00:00:00+00:00'; p=predict(engineer(data).iloc[-1].to_dict())
    if not p['available']: pytest.skip('Run model training to enable artifact-dependent inference test')
    assert 0<=p['fraud_probability']<=1 and 0<=p['anomaly_score']<=1
    assert p['model_version'] and p['explanation']

def test_historical_prediction_rejects_hindsight():
    p=predict(engineer(generate(30)).iloc[-1].to_dict())
    if not p['model_version']: pytest.skip('Train a baseline model first')
    assert p['available'] is False
    assert p['fraud_probability'] is None
    assert 'Temporal guard' in p['limitation']

def test_origin_protection(admin):
    assert admin.post('/api/auth/logout',headers={'Origin':'https://untrusted.example'}).status_code==403

def test_risk_breakdown_is_priority_not_probability():
    from backend.app.agents.specialists import risk
    ctx={'transaction':generate(1).iloc[0].to_dict(),'settings':copy.deepcopy(DEFAULT_SETTINGS)}
    outputs={name:{'score':.5,'confidence':.8} for name in DEFAULT_SETTINGS['weights']}
    assessed=risk(ctx,outputs)
    assert assessed['details']['priority']==pytest.approx(50)
    assert assessed['details']['category']=='medium'
    assert sum(part['contribution'] for part in assessed['details']['breakdown'].values())==pytest.approx(50)
    assert 'not a fraud probability' in assessed['findings'][0]

def test_supervisor_timeout_stops_dependent_stages(monkeypatch):
    import time
    data=generate(30);t=data.iloc[-1].to_dict();f=engineer(data).iloc[-1].to_dict()
    configured=copy.deepcopy(DEFAULT_SETTINGS);configured['investigation_timeout_seconds']=.01
    def slow(ctx,outputs):
        time.sleep(.05)
        return SPECIALISTS['transaction'](ctx,outputs)
    monkeypatch.setitem(SPECIALISTS,'graph',slow)
    ctx={'transaction':t,'features':f,'prior':data.iloc[:-1].to_dict('records'),'verified_cases':[],'settings':configured,'run_id':'synthetic-timeout'}
    state=Supervisor().run(ctx)
    assert state['phase']=='incomplete'
    assert any(log['status']=='timeout' for log in state['logs'])
    assert 'reporting' not in state['results']
