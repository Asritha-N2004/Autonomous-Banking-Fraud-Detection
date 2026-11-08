import pandas as pd
from sqlalchemy import select
from ..database import Account, Customer, Beneficiary, Device, Merchant, Transaction
from ..schemas import TransactionInput

def serialize(row):
    return {c.name:getattr(row,c.name) for c in row.__table__.columns}

def ingest(db, values):
    parsed=[v if isinstance(v,TransactionInput) else TransactionInput.model_validate(v) for v in values]
    ids=[t.id for t in parsed]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate transaction IDs in batch')
    existing=set(db.scalars(select(Transaction.id).where(Transaction.id.in_(ids))).all())
    if existing: raise ValueError(f'Duplicate transaction IDs: {sorted(existing)[:5]}')
    for t in parsed:
        if not db.get(Account,t.account_id):
            cid=f'customer-{t.account_id}'
            # Internal grouping only; no real customer identity or KYC ownership is inferred.
            if not db.get(Customer,cid): db.add(Customer(id=cid,synthetic=True)); db.flush()
            db.add(Account(id=t.account_id,customer_id=cid)); db.flush()
        for model,identifier in [(Beneficiary,t.beneficiary_id),(Device,t.device_id),(Merchant,t.merchant_id)]:
            if identifier and not db.get(model,identifier): db.add(model(id=identifier)); db.flush()
        values=t.model_dump(mode='json')
        db.add(Transaction(**values))
    db.flush()
    return len(parsed)

def frame(db, as_of=None):
    query=select(Transaction).order_by(Transaction.timestamp,Transaction.id)
    if as_of: query=query.where(Transaction.timestamp<=as_of)
    rows=[serialize(t) for t in db.scalars(query).all()]
    return pd.DataFrame(rows)
