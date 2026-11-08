"""Explicit user-supplied CSV adapters. No licensed dataset is silently downloaded."""
import pandas as pd
from ..schemas import TransactionInput

def load_csv(path,kind='canonical',synthetic=False):
    data=pd.read_csv(path)
    if kind=='paysim':
        required={'step','type','amount','nameOrig','nameDest','isFraud'}
        if not required<=set(data): raise ValueError(f'PaySim requires {sorted(required)}')
        epoch=pd.Timestamp('2025-01-01',tz='UTC')
        data=pd.DataFrame({'id':['PS-'+str(i) for i in range(len(data))],'account_id':data.nameOrig,'beneficiary_id':data.nameDest,
            'timestamp':[(epoch+pd.Timedelta(hours=int(h))).isoformat() for h in data.step],'amount':data.amount,
            'transaction_type':data.type.map({'TRANSFER':'transfer','PAYMENT':'purchase','CASH_OUT':'withdrawal','CASH_IN':'deposit','DEBIT':'withdrawal'}),
            'channel':'mobile','currency':'XXX','synthetic':True,'historical_label':data.isFraud,'source':'user-supplied-paysim'})
    elif kind=='banksim':
        required={'step','customer','merchant','amount','fraud'}
        if not required<=set(data): raise ValueError(f'BankSim requires {sorted(required)}')
        epoch=pd.Timestamp('2025-01-01',tz='UTC')
        data=pd.DataFrame({'id':['BS-'+str(i) for i in range(len(data))],'account_id':data.customer.astype(str).str.strip("'"),
            'beneficiary_id':data.merchant.astype(str).str.strip("'"),'merchant_id':data.merchant.astype(str).str.strip("'"),
            'timestamp':[(epoch+pd.Timedelta(days=int(h))).isoformat() for h in data.step],'amount':data.amount,
            'transaction_type':'purchase','channel':'web','currency':'XXX','synthetic':True,'historical_label':data.fraud,'source':'user-supplied-banksim'})
    elif kind!='canonical':
        raise ValueError('Supported: canonical, paysim, banksim. Anonymized card/IEEE data lack verified account links; do not invent graph entities.')
    else:
        data['synthetic']=synthetic
        if 'source' not in data: data['source']='user-supplied-canonical-csv'
    records=[]
    for row in data.to_dict('records'):
        clean={k:v for k,v in row.items() if not pd.isna(v)}
        records.append(TransactionInput.model_validate(clean).model_dump(mode='json'))
    return pd.DataFrame(records)
