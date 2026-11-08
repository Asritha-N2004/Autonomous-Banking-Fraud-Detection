import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.ml.adapters import load_csv
from backend.app.database import init_db,SessionLocal
from backend.app.services.transactions import ingest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('path');p.add_argument('--kind',choices=['canonical','paysim','banksim'],default='canonical');p.add_argument('--synthetic',action='store_true');a=p.parse_args()
    rows=load_csv(a.path,a.kind,a.synthetic);init_db()
    with SessionLocal() as db:
        count=ingest(db,rows.to_dict('records'));db.commit();print(f'Imported {count} validated records. Review source licensing separately.')
