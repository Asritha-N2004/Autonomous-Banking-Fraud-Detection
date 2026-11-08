from uuid import uuid4
from sqlalchemy import select
from ..database import Transaction, Investigation, Evidence, AgentRun, AgentLog, Alert, Prediction, Setting
from ..config import DEFAULT_SETTINGS
from ..ml.features import engineer
from ..agents.supervisor import Supervisor
from .transactions import serialize, frame

def settings(db):
    row=db.get(Setting,'runtime')
    return row.payload if row else DEFAULT_SETTINGS.copy()

def investigate(db, transaction_id, user):
    transaction=db.get(Transaction,transaction_id)
    if not transaction: raise LookupError('Transaction not found')
    t=serialize(transaction)
    snapshot=frame(db,t['timestamp'])
    features=engineer(snapshot)
    features=features[features.id==transaction_id].iloc[0].to_dict()
    prior=[r for r in snapshot.to_dict('records') if r['timestamp']<t['timestamp']]
    verified=[]
    for c in db.scalars(select(Investigation).where(Investigation.status=='closed')).all():
        if c.review and c.review['outcome']=='confirmed_fraud' and c.review['timestamp']<t['timestamp']:
            ct=db.get(Transaction,c.transaction_id)
            verified.append({'case_id':c.id,'transaction_id':ct.id,'account_id':ct.account_id,'beneficiary_id':ct.beneficiary_id})
    ctx={'transaction':t,'features':features,'prior':prior,'verified_cases':verified,'settings':settings(db),'run_id':str(uuid4())}
    state=Supervisor().run(ctx)
    if 'reporting' not in state['results']:
        run=AgentRun(id=ctx['run_id'],status='failed',duration_ms=state['duration_ms']); db.add(run); db.flush()
        for log in state['logs']: db.add(AgentLog(run_id=run.id,agent=log['agent'],payload=log))
        db.commit()
        raise RuntimeError('Investigation incomplete; inspect agent logs')
    risk=state['results']['risk']['details']
    report=state['results']['reporting']['details']
    report['supervisor_review']=state['supervisor_review']
    case=Investigation(transaction_id=transaction_id,assigned_to=user.id,priority=risk['priority'],category=risk['category'],report=report)
    db.add(case); db.flush()
    run=AgentRun(id=ctx['run_id'],case_id=case.id,status='awaiting_human_review',duration_ms=state['duration_ms']); db.add(run); db.flush()
    for log in state['logs']: db.add(AgentLog(run_id=run.id,agent=log['agent'],payload=log))
    for item in report['evidence']: db.add(Evidence(case_id=case.id,payload=item))
    db.add(Prediction(transaction_id=transaction_id,payload=state['results']['ml']['details'] if 'ml' in state['results'] else {'available':False}))
    if risk['priority']>=settings(db)['thresholds']['medium']:
        db.add(Alert(transaction_id=transaction_id,case_id=case.id,priority=risk['priority'],category=risk['category']))
    db.flush()
    return case,run
