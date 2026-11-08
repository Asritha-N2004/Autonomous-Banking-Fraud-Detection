"""Idempotent initial setup of an explicitly configured hosted research database."""
import os
import json
from sqlalchemy import select, func, text
from ..database import SessionLocal, Role, User, Transaction, ModelVersion, ModelMetric
from ..config import MODEL_PATH
from ..security import ROLES, hash_password

def initialize_hosted_workspace():
    if os.getenv('VERCEL')!='1':
        return
    with SessionLocal() as db:
        # Serialize initial setup across cold starts sharing the PostgreSQL database.
        db.execute(text('SELECT pg_advisory_xact_lock(682143901)'))
        for name in ROLES:
            if not db.get(Role,name): db.add(Role(name=name))
        db.flush()
        username=os.getenv('ADMIN_USERNAME','admin')
        if not db.scalar(select(User.id).where(User.username==username)):
            password=os.getenv('ADMIN_PASSWORD','')
            if len(password)<12:
                raise RuntimeError('Set a private ADMIN_PASSWORD of at least 12 characters in Vercel.')
            db.add(User(username=username,password_hash=hash_password(password),role='ADMIN'))
        if os.getenv('SEED_SYNTHETIC_DATA','false').lower()=='true' and not db.scalar(select(func.count(Transaction.id))):
            from ..ml.data import generate
            from .transactions import ingest
            ingest(db,generate(2400,42).to_dict('records'))
        metadata_path=MODEL_PATH.with_suffix('.json')
        if metadata_path.exists():
            metadata=json.loads(metadata_path.read_text())
            if not db.get(ModelVersion,metadata['version']):
                db.add(ModelVersion(id=metadata['version'],payload=metadata));db.flush()
                db.add(ModelMetric(model_version=metadata['version'],payload=metadata['metrics']))
        db.commit()
