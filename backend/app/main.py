import csv
import io
import json
import logging
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .database import *
from .security import current_user, roles, hash_password, verify_password, create_session, audit, case_access, token_digest, ROLES
from .schemas import TransactionInput, Login, UserInput, Registration, Analyze, ReviewInput, NoteInput, CaseUpdate, SettingsInput
from .services.transactions import ingest, serialize, frame
from .services.investigations import investigate, settings
from .graph.analytics import build_graph, metrics as graph_metrics, neighborhood
from .ml.training import train
from .config import MODEL_PATH, allowed_origins

logger=logging.getLogger('banking.api')
READ=roles('ADMIN','ANALYST','SUPERVISOR','AUDITOR')
OPERATE=roles('ADMIN','SUPERVISOR','FRAUD_INVESTIGATOR')
ADMIN=roles('ADMIN')

@asynccontextmanager
async def lifespan(app):
    init_db()
    from .services.cloud_setup import initialize_hosted_workspace
    initialize_hosted_workspace()
    yield

app=FastAPI(title='Sentinel | Hierarchical Banking Fraud Investigation',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=allowed_origins(),allow_credentials=True,allow_methods=['GET','POST','PATCH'],allow_headers=['Content-Type','Authorization'])
requests_by_ip=defaultdict(deque)

@app.middleware('http')
async def security_headers(request,call_next):
    start=time.perf_counter(); host=request.client.host if request.client else 'unknown'
    key=(host,request.url.path in ['/api/auth/login','/api/auth/register'])
    queue=requests_by_ip[key]; current=time.monotonic()
    while queue and queue[0]<current-60: queue.popleft()
    limit=20 if key[1] else 300
    if len(queue)>=limit: return JSONResponse({'detail':'Rate limit exceeded'},status_code=429,headers={'Retry-After':'60'})
    queue.append(current)
    # Same-site cookie writes are protected against cross-origin requests; bearer tools remain supported.
    if request.method in ['POST','PATCH','DELETE'] and request.cookies.get('bank_session') and not request.headers.get('Authorization'):
        origin=request.headers.get('origin')
        if origin and origin not in allowed_origins():
            return JSONResponse({'detail':'Origin rejected'},status_code=403)
    response=await call_next(request)
    response.headers.update({'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Cache-Control':'no-store'})
    logger.info(json.dumps({'method':request.method,'path':request.url.path,'status':response.status_code,'duration_ms':round((time.perf_counter()-start)*1000,2)}))
    return response

def get_or_404(db,model,identifier):
    row=db.get(model,identifier)
    if not row: raise HTTPException(404,f'{model.__name__} not found')
    return row

def case_query(user):
    query=select(Investigation)
    if user.role=='FRAUD_INVESTIGATOR': query=query.where(Investigation.assigned_to==user.id)
    return query

def case_read(db,user,identifier):
    case=get_or_404(db,Investigation,identifier); case_access(user,case)
    return case

@app.get('/api/health')
def health(): return {'status':'ok','model_available':MODEL_PATH.exists(),'mode':'research_decision_support'}

@app.post('/api/auth/login')
def login(body:Login,response:Response,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(func.lower(User.username)==body.username.strip().lower()))
    if not user or not user.active or not verify_password(body.password,user.password_hash): raise HTTPException(401,'Invalid credentials')
    hours=int(os.getenv('SESSION_HOURS','8')); token=create_session(db,user,hours)
    response.set_cookie('bank_session',token,httponly=True,secure=os.getenv('COOKIE_SECURE','false').lower()=='true',samesite='strict',max_age=hours*3600)
    audit(db,user,'login'); db.commit()
    return {'user':{'id':user.id,'username':user.username,'role':user.role}}

@app.post('/api/auth/register', status_code=201)
def register(body:Registration,response:Response,db:Session=Depends(get_db)):
    if db.scalar(select(User.id).where(func.lower(User.username)==body.username)):
        raise HTTPException(409,'Username is already taken. Choose another or sign in.')
    if not db.get(Role,'ANALYST'):
        raise HTTPException(503,'Account setup is unavailable. An administrator must bootstrap the workspace first.')
    user=User(username=body.username,password_hash=hash_password(body.password),role='ANALYST')
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Username is already taken. Choose another or sign in.')
    audit(db,user,'self_register',user.id,{'role':'ANALYST'})
    hours=int(os.getenv('SESSION_HOURS','8'))
    token=create_session(db,user,hours)
    response.set_cookie('bank_session',token,httponly=True,secure=os.getenv('COOKIE_SECURE','false').lower()=='true',samesite='strict',max_age=hours*3600)
    return {'user':{'id':user.id,'username':user.username,'role':user.role}}

@app.post('/api/auth/logout')
def logout(request:Request,response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
    auth=request.headers.get('Authorization','')
    token=auth[7:] if auth.startswith('Bearer ') else request.cookies.get('bank_session','')
    db.execute(delete(SessionToken).where(SessionToken.token_hash==token_digest(token)))
    audit(db,user,'logout'); db.commit(); response.delete_cookie('bank_session')
    return {'status':'logged_out'}

@app.get('/api/auth/me')
def me(user:User=Depends(current_user)): return {'id':user.id,'username':user.username,'role':user.role}

@app.get('/api/users')
def users(user:User=Depends(roles('ADMIN','SUPERVISOR')),db:Session=Depends(get_db)):
    return [{'id':u.id,'username':u.username,'role':u.role} for u in db.scalars(select(User)).all()]

@app.post('/api/users',status_code=201)
def add_user(body:UserInput,user:User=Depends(ADMIN),db:Session=Depends(get_db)):
    if len(body.password)<12: raise HTTPException(422,'Password must contain at least 12 characters')
    if db.scalar(select(User).where(User.username==body.username)): raise HTTPException(409,'Username exists')
    row=User(username=body.username,password_hash=hash_password(body.password),role=body.role); db.add(row); db.flush()
    audit(db,user,'create_user',row.id,{'role':row.role}); db.commit()
    return {'id':row.id,'username':row.username,'role':row.role}

@app.post('/api/transactions',status_code=201)
def add_transaction(body:TransactionInput,user:User=Depends(roles('ADMIN','SUPERVISOR')),db:Session=Depends(get_db)):
    try: ingest(db,[body])
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,user,'ingest_transaction',body.id); db.commit()
    return serialize(db.get(Transaction,body.id))

@app.post('/api/transactions/batch',status_code=201)
def batch(body:list[TransactionInput],user:User=Depends(roles('ADMIN','SUPERVISOR')),db:Session=Depends(get_db)):
    if len(body)>5000 or not body: raise HTTPException(422,'Batch size must be 1–5000')
    try: count=ingest(db,body)
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,user,'ingest_batch',payload={'count':count}); db.commit()
    return {'ingested':count}

@app.get('/api/transactions')
def transactions(q:str='',channel:str|None=None,sort:str='timestamp',direction:str='desc',offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),user:User=Depends(READ),db:Session=Depends(get_db)):
    query=select(Transaction)
    if q: query=query.where(Transaction.id.contains(q,autoescape=True)|Transaction.account_id.contains(q,autoescape=True))
    if channel: query=query.where(Transaction.channel==channel)
    count=db.scalar(select(func.count()).select_from(query.subquery()))
    column={'timestamp':Transaction.timestamp,'amount':Transaction.amount,'id':Transaction.id}.get(sort)
    if column is None or direction not in ['asc','desc']: raise HTTPException(422,'Invalid sorting')
    items=[]
    for t in db.scalars(query.order_by(column.desc() if direction=='desc' else column.asc()).offset(offset).limit(limit)):
        value=serialize(t)
        c=db.scalar(select(Investigation).where(Investigation.transaction_id==t.id).order_by(Investigation.created_at.desc()))
        predictions=db.scalars(select(Prediction).where(Prediction.transaction_id==t.id)).all()
        p=max(predictions,key=lambda row:row.payload.get('prediction_timestamp',''),default=None)
        value.update({'priority':c.priority if c else None,'review_status':c.status if c else 'not_analyzed','prediction':p.payload if p else None})
        items.append(value)
    return {'items':items,'total':count,'offset':offset,'limit':limit}

@app.get('/api/transactions/{transaction_id}')
def transaction_detail(transaction_id:str,user:User=Depends(READ),db:Session=Depends(get_db)):
    return serialize(get_or_404(db,Transaction,transaction_id))

def analyze(body,user,db):
    try: case,run=investigate(db,body.transaction_id,user)
    except LookupError as exc: raise HTTPException(404,str(exc))
    except RuntimeError as exc: raise HTTPException(503,str(exc))
    audit(db,user,'investigate',case.id,{'transaction_id':body.transaction_id,'run_id':run.id}); db.commit()
    return {'case_id':case.id,'run_id':run.id,'priority':case.priority,'category':case.category,'status':case.status}

@app.post('/api/fraud/analyze')
@app.post('/api/investigations')
@app.post('/api/agents/run')
def start_analysis(body:Analyze,user:User=Depends(OPERATE),db:Session=Depends(get_db)): return analyze(body,user,db)

@app.get('/api/fraud/alerts')
def alerts(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),user:User=Depends(READ),db:Session=Depends(get_db)):
    return {'items':[serialize(a) for a in db.scalars(select(Alert).order_by(Alert.priority.desc()).offset(offset).limit(limit))], 'total':db.scalar(select(func.count(Alert.id)))}

@app.get('/api/fraud/alerts/{alert_id}')
def alert(alert_id:str,user:User=Depends(READ),db:Session=Depends(get_db)): return serialize(get_or_404(db,Alert,alert_id))

@app.get('/api/investigations')
def cases(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),user:User=Depends(current_user),db:Session=Depends(get_db)):
    if user.role=='ANALYST': raise HTTPException(403,'Case access requires investigator role')
    query=case_query(user)
    return {'items':[{k:v for k,v in serialize(c).items() if k!='report'} for c in db.scalars(query.order_by(Investigation.created_at.desc()).offset(offset).limit(limit))],
        'total':db.scalar(select(func.count()).select_from(query.subquery()))}

@app.get('/api/investigations/{case_id}')
def case_detail(case_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    case=case_read(db,user,case_id)
    value=serialize(case); value['notes']=[serialize(n) for n in db.scalars(select(Note).where(Note.case_id==case_id).order_by(Note.timestamp))]
    return value

@app.patch('/api/investigations/{case_id}')
def update_case(case_id:str,body:CaseUpdate,user:User=Depends(OPERATE),db:Session=Depends(get_db)):
    case=case_read(db,user,case_id)
    if case.status=='closed': raise HTTPException(409,'Closed cases are immutable')
    if body.assigned_to:
        if user.role not in ['ADMIN','SUPERVISOR']: raise HTTPException(403,'Supervisor required to assign')
        assignee=get_or_404(db,User,body.assigned_to)
        if assignee.role not in ['ADMIN','SUPERVISOR','FRAUD_INVESTIGATOR']: raise HTTPException(422,'Assignee must be an investigator')
        case.assigned_to=assignee.id
    if body.status: case.status=body.status
    case.updated_at=now(); audit(db,user,'update_case',case_id,body.model_dump(exclude_none=True)); db.commit()
    return {'status':case.status,'assigned_to':case.assigned_to}

@app.post('/api/investigations/{case_id}/notes')
def add_note(case_id:str,body:NoteInput,user:User=Depends(OPERATE),db:Session=Depends(get_db)):
    case_read(db,user,case_id)
    row=Note(case_id=case_id,user_id=user.id,text=body.text); db.add(row)
    audit(db,user,'add_note',case_id); db.commit(); return serialize(row)

@app.post('/api/investigations/{case_id}/review')
def review_case(case_id:str,body:ReviewInput,user:User=Depends(roles('ADMIN','SUPERVISOR')),db:Session=Depends(get_db)):
    case=case_read(db,user,case_id)
    if case.status=='closed': raise HTTPException(409,'Case already closed')
    evidence_ids=list(db.scalars(select(Evidence.id).where(Evidence.case_id==case_id)))
    case.review={**body.model_dump(),'reviewer_id':user.id,'timestamp':now(),'supporting_evidence':evidence_ids,'policy_version':case.report['policy']['policy_version']}
    case.status='in_progress' if body.decision=='request_more_information' else 'closed'
    case.updated_at=now()
    for a in db.scalars(select(Alert).where(Alert.case_id==case.id)):
        a.status=body.outcome if case.status=='closed' else 'unverified'
    audit(db,user,'human_review',case_id,case.review); db.commit()
    return {'status':case.status,'review':case.review,'banking_actions_executed':False}

@app.get('/api/evidence')
def evidence(case_id:str|None=None,offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=200),user:User=Depends(current_user),db:Session=Depends(get_db)):
    if user.role=='ANALYST': raise HTTPException(403,'Evidence access denied')
    query=select(Evidence).join(Investigation)
    if user.role=='FRAUD_INVESTIGATOR': query=query.where(Investigation.assigned_to==user.id)
    if case_id: case_read(db,user,case_id); query=query.where(Evidence.case_id==case_id)
    return {'items':[serialize(e) for e in db.scalars(query.offset(offset).limit(limit))], 'total':db.scalar(select(func.count()).select_from(query.subquery()))}

@app.get('/api/investigations/{case_id}/report')
def report(case_id:str,format:str='json',user:User=Depends(OPERATE),db:Session=Depends(get_db)):
    case=case_read(db,user,case_id)
    data=serialize(case); data['notes']=[serialize(n) for n in db.scalars(select(Note).where(Note.case_id==case_id))]
    audit(db,user,'export_report',case_id,{'format':format}); db.commit()
    if format=='json': return data
    if format=='csv':
        stream=io.StringIO(); writer=csv.writer(stream)
        writer.writerow(['evidence_id','type','timestamp','description','references','quality','provenance'])
        for e in case.report['evidence']:
            values=[e['id'],e['type'],e['timestamp'],e['description'],json.dumps(e['references']),e['quality'],json.dumps(e['provenance'])]
            writer.writerow(["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for v in values])
        return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="case-{case.id}.csv"'})
    if format=='pdf':
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from xml.sax.saxutils import escape
        buffer=io.BytesIO(); styles=getSampleStyleSheet(); story=[]
        def paragraph(text,style='BodyText'): story.append(Paragraph(escape(str(text)),styles[style])); story.append(Spacer(1,8))
        paragraph('Banking Investigation Report','Title'); paragraph(f'Case {case.id} | {case.created_at} | {case.status}')
        for title,value in [('Transaction details',case.report['transaction']),('Consolidated risk assessment',case.report['risk_assessment']),('Investigation and recommendations',case.report['investigation']),('Agent findings',case.report['agent_findings']),('Policy checks',case.report['policy']),('Limitations',case.report['limitations']),('Human review',case.review),('Reviewer notes',data['notes'])]:
            paragraph(title,'Heading2')
            # Keep paragraphs small so long reports paginate reliably.
            for line in json.dumps(value,indent=2).splitlines(): paragraph(line)
        paragraph('Evidence summary','Heading2')
        for e in case.report['evidence']: paragraph(f"{e['id']} | {e['timestamp']} | {e['description']} | References: {', '.join(e['references'])} | Provenance: {e['source']}")
        SimpleDocTemplate(buffer).build(story)
        return Response(buffer.getvalue(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="case-{case.id}.pdf"'})
    raise HTTPException(422,'Supported formats: json, csv, pdf')

@app.get('/api/agents/runs')
def runs(user:User=Depends(current_user),db:Session=Depends(get_db)):
    query=select(AgentRun)
    if user.role=='FRAUD_INVESTIGATOR': query=query.join(Investigation).where(Investigation.assigned_to==user.id)
    if user.role=='ANALYST': raise HTTPException(403,'Agent trace access denied')
    return {'items':[serialize(r) for r in db.scalars(query.order_by(AgentRun.created_at.desc()).limit(100))]}

def run_access(db,user,run_id):
    run=get_or_404(db,AgentRun,run_id)
    if user.role=='ANALYST': raise HTTPException(403,'Agent trace access denied')
    if run.case_id: case_read(db,user,run.case_id)
    elif user.role not in ['ADMIN','SUPERVISOR','AUDITOR']: raise HTTPException(403,'Run access denied')
    return run

@app.get('/api/agents/status/{run_id}')
def run_status(run_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)): return serialize(run_access(db,user,run_id))

@app.get('/api/agents/logs/{run_id}')
def run_logs(run_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    run_access(db,user,run_id)
    return {'items':[serialize(l) for l in db.scalars(select(AgentLog).where(AgentLog.run_id==run_id))]}

def graph_snapshot(db,as_of=None): return build_graph(frame(db,as_of).to_dict('records'))

@app.get('/api/graph/statistics')
def graph_stats(as_of:str|None=None,user:User=Depends(READ),db:Session=Depends(get_db)): return graph_metrics(graph_snapshot(db,as_of))

@app.get('/api/graph/neighborhood/{node_id}')
def graph_neighbors(node_id:str,hops:int=Query(1,ge=1,le=2),as_of:str|None=None,user:User=Depends(READ),db:Session=Depends(get_db)):
    return neighborhood(graph_snapshot(db,as_of),node_id,hops)

@app.get('/api/graph/relationships/{node_id}')
def graph_relationships(node_id:str,user:User=Depends(READ),db:Session=Depends(get_db)): return neighborhood(graph_snapshot(db),node_id,1)

@app.get('/api/graph/path')
def graph_path(source:str,target:str,user:User=Depends(READ),db:Session=Depends(get_db)):
    import networkx as nx
    g=graph_snapshot(db)
    try: path=nx.shortest_path(g,source,target)
    except (nx.NetworkXNoPath,nx.NodeNotFound): return {'path':[],'relationships':[]}
    return {'path':path,'relationships':[list(g[a][b].values()) for a,b in zip(path,path[1:])]}

@app.get('/api/graph/investigation/{case_id}')
def case_graph(case_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    case=case_read(db,user,case_id); t=db.get(Transaction,case.transaction_id)
    return neighborhood(graph_snapshot(db,t.timestamp),'account:'+t.account_id,2)

@app.get('/api/models')
def models(user:User=Depends(READ),db:Session=Depends(get_db)): return {'items':[serialize(m) for m in db.scalars(select(ModelVersion))]}

@app.get('/api/models/metrics')
def model_metrics(user:User=Depends(READ),db:Session=Depends(get_db)):
    path=MODEL_PATH.with_suffix('.json')
    result=json.loads(path.read_text()) if path.exists() else {'metrics':{},'limitation':'Train models first'}
    advanced=MODEL_PATH.parent/'advanced.json'
    if advanced.exists(): result['advanced_offline_experiment']=json.loads(advanced.read_text())
    return result

@app.post('/api/models/train')
def train_models(user:User=Depends(ADMIN),db:Session=Depends(get_db)):
    if os.getenv('VERCEL')=='1':
        raise HTTPException(409,'Hosted model files are read-only. Train during a new deployment build.')
    # Human outcomes remain separate; no self-training on predictions.
    data=frame(db)
    if data.empty or not data.synthetic.all(): raise HTTPException(422,'API training is restricted to explicit synthetic benchmarks; use controlled offline ingestion for verified datasets')
    try: metadata=train(data)
    except ValueError as exc: raise HTTPException(422,str(exc))
    db.merge(ModelVersion(id=metadata['version'],payload=metadata)); db.flush()
    db.add(ModelMetric(model_version=metadata['version'],payload=metadata['metrics']))
    audit(db,user,'train_models',metadata['version']); db.commit()
    return metadata

@app.post('/api/models/evaluate')
def evaluate_models(user:User=Depends(ADMIN),db:Session=Depends(get_db)):
    result=model_metrics(user,db); audit(db,user,'read_stored_evaluation'); db.commit()
    return {'evaluation_type':'stored held-out test evaluation from latest training; no retraining',**result}

@app.get('/api/analytics/dashboard')
@app.get('/api/fraud/statistics')
def dashboard(user:User=Depends(READ),db:Session=Depends(get_db)):
    return {'total_transactions':db.scalar(select(func.count(Transaction.id))), 'analyzed_transactions':db.scalar(select(func.count(func.distinct(Prediction.transaction_id)))),
        'alerts':db.scalar(select(func.count(Alert.id))), 'open_investigations':db.scalar(select(func.count(Investigation.id)).where(Investigation.status!='closed')),
        'high_priority_cases':db.scalar(select(func.count(Investigation.id)).where(Investigation.category.in_(['high','critical']))),
        'confirmed_human_outcomes':sum(1 for c in db.scalars(select(Investigation)) if c.review and c.status=='closed' and c.review['outcome']=='confirmed_fraud'),
        'simulated_historical_fraud_labels':db.scalar(select(func.count(Transaction.id)).where(Transaction.synthetic==True,Transaction.historical_label==1)),
        'synthetic_transactions':db.scalar(select(func.count(Transaction.id)).where(Transaction.synthetic==True)),
        'agent_runs':db.scalar(select(func.count(AgentRun.id))), 'model_available':MODEL_PATH.exists()}

@app.get('/api/analytics/transaction-trends')
def transaction_trends(user:User=Depends(READ),db:Session=Depends(get_db)):
    day=func.substr(Transaction.timestamp,1,10)
    rows=db.execute(select(day.label('date'),func.count().label('count'),func.sum(Transaction.amount).label('amount')).group_by(day).order_by(day)).all()
    return {'items':[dict(r._mapping) for r in rows]}

@app.get('/api/analytics/fraud-trends')
def fraud_trends(user:User=Depends(READ),db:Session=Depends(get_db)):
    day=func.substr(Transaction.timestamp,1,10)
    rows=db.execute(select(day.label('date'),func.count(Alert.id).label('alerts')).join(Alert,Transaction.id==Alert.transaction_id).group_by(day).order_by(day)).all()
    return {'items':[dict(r._mapping) for r in rows]}

@app.get('/api/analytics/agent-performance')
def agent_performance(user:User=Depends(READ),db:Session=Depends(get_db)):
    stats=defaultdict(list)
    for log in db.scalars(select(AgentLog)): stats[log.agent].append(log.payload)
    return {'items':[{'agent':name,'runs':len(logs),'mean_duration_ms':sum(l['duration_ms'] for l in logs)/len(logs),'failures':sum(l['status']!='completed' for l in logs)} for name,logs in stats.items()]}

@app.get('/api/settings')
def read_settings(user:User=Depends(ADMIN),db:Session=Depends(get_db)): return settings(db)

@app.patch('/api/settings')
def update_settings(body:SettingsInput,user:User=Depends(ADMIN),db:Session=Depends(get_db)):
    weights=body.weights; thresholds=body.thresholds
    if set(weights)!={'transaction','behavioral','account','graph','ml','pattern'} or any(not 0<=v<=1 for v in weights.values()) or abs(sum(weights.values())-1)>1e-6: raise HTTPException(422,'Six nonnegative weights must sum to 1')
    if set(thresholds)!={'medium','high','critical'} or not 0<thresholds['medium']<thresholds['high']<thresholds['critical']<=100: raise HTTPException(422,'Thresholds must increase within (0,100]')
    db.merge(Setting(key='runtime',payload=body.model_dump())); audit(db,user,'update_settings',payload=body.model_dump()); db.commit()
    return body

@app.get('/api/audit')
def audit_logs(offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=200),user:User=Depends(roles('ADMIN','AUDITOR')),db:Session=Depends(get_db)):
    return {'items':[serialize(a) for a in db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit))]}
