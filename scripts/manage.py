"""Reproducible local commands. Execute from the repository root."""
import argparse
import json
import os
import sys
from pathlib import Path
from sqlalchemy import select
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.database import *
from backend.app.ml.data import generate
from backend.app.ml.features import engineer
from backend.app.ml.training import train
from backend.app.services.transactions import ingest, frame
from backend.app.schemas import TransactionInput
from backend.app.security import hash_password, ROLES
from backend.app.config import ROOT, MODEL_PATH

def main(command=None):
    parser=argparse.ArgumentParser()
    if command is None: parser.add_argument('command',choices=['bootstrap','generate','ingest','preprocess','graph','train','evaluate','demo','migrate'])
    parser.add_argument('--input',default=str(ROOT/'data/synthetic/transactions.csv'))
    parser.add_argument('--rows',type=int,default=2400)
    parser.add_argument('--seed',type=int,default=42)
    args=parser.parse_args(); command=command or args.command
    if command=='generate':
        path=Path(args.input); path.parent.mkdir(parents=True,exist_ok=True); generate(args.rows,args.seed).to_csv(path,index=False)
        print(f'Generated {args.rows} explicitly synthetic records: {path}'); return
    if command=='preprocess':
        import pandas as pd
        data=pd.read_csv(args.input)
        for row in data.to_dict('records'): TransactionInput.model_validate(row)
        out=ROOT/'data/processed/features.csv'; out.parent.mkdir(parents=True,exist_ok=True)
        engineer(data).to_csv(out,index=False); print(out); return
    if command=='evaluate':
        print(MODEL_PATH.with_suffix('.json').read_text()); return
    init_db()
    with SessionLocal() as db:
        if command=='migrate':
            from sqlalchemy import text
            db.execute(text('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)'))
            if not db.execute(text('SELECT version FROM schema_migrations WHERE version=1')).first(): db.execute(text('INSERT INTO schema_migrations (version) VALUES (1)'))
            db.commit(); print('Schema migration 1 applied'); return
        if command=='bootstrap':
            for role in ROLES: db.merge(Role(name=role))
            db.flush()
            username=os.getenv('ADMIN_USERNAME','admin'); password=os.getenv('ADMIN_PASSWORD','')
            if not db.scalar(select(User).where(User.username==username)):
                if len(password)<12: raise SystemExit('Set ADMIN_PASSWORD to a unique password of at least 12 characters before bootstrap.')
                db.add(User(username=username,password_hash=hash_password(password),role='ADMIN'))
            db.commit(); print('Roles and administrator initialized'); return
        if command=='ingest':
            import pandas as pd
            data=pd.read_csv(args.input).where(lambda x:x.notna(),None)
            rows=data.to_dict('records')
            count=ingest(db,rows); db.commit(); print(f'Ingested {count} records'); return
        if command=='train':
            data=frame(db)
            if data.empty:
                import pandas as pd
                data=pd.read_csv(args.input)
            metadata=train(data); db.merge(ModelVersion(id=metadata['version'],payload=metadata)); db.flush()
            db.add(ModelMetric(model_version=metadata['version'],payload=metadata['metrics'])); db.commit()
            print(json.dumps(metadata,indent=2)); return
        if command=='graph':
            from backend.app.graph.analytics import build_graph,persist,metrics
            g=build_graph(frame(db).to_dict('records')); persist(db,g); db.commit()
            result=metrics(g); (ROOT/'data/processed/graph_metrics.json').write_text(json.dumps(result,indent=2)); print(f'Persisted {len(g)} entities and {g.number_of_edges()} relationships'); return
        if command=='demo':
            from backend.app.services.investigations import investigate
            user=db.scalar(select(User).where(User.role=='ADMIN'))
            if not user: raise SystemExit('Bootstrap an administrator first')
            existing=set(db.scalars(select(Investigation.transaction_id)))
            # Select solely by observed amounts, never ground-truth labels.
            import pandas as pd
            metadata=json.loads(MODEL_PATH.with_suffix('.json').read_text())
            cutoff=pd.Timestamp(metadata['split_end_times']['validation']).isoformat()
            ids=list(db.scalars(select(Transaction.id).where(Transaction.timestamp>cutoff).order_by(Transaction.amount.desc()).limit(12)))
            for identifier in ids:
                if identifier not in existing:
                    case,run=investigate(db,identifier,user); db.commit(); print(f'{identifier}: case {case.id} priority {case.priority:.1f}')

if __name__=='__main__': main()
