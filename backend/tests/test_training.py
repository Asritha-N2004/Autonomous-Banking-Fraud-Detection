import json
import pytest
from backend.app.ml.training import train
from backend.app.ml.data import generate
from backend.app.ml.adapters import load_csv

def test_actual_training_and_temporal_metrics(tmp_path):
    metadata=train(generate(400),tmp_path/'synthetic-model.joblib')
    assert metadata['splits']=={'train':240,'validation':80,'test':80}
    assert metadata['split_end_times']['train']<metadata['split_end_times']['validation']<metadata['split_end_times']['test']
    assert metadata['runtime']['scikit-learn']
    for name in ['logistic_regression','random_forest','gradient_boosting']:
        metrics=metadata['metrics'][name]
        assert sum(map(sum,metrics['confusion_matrix']))==80
        assert 0<=metrics['pr_auc']<=1
    assert json.loads((tmp_path/'synthetic-model.json').read_text())['data_sha256']==metadata['data_sha256']

def test_paysim_adapter_does_not_invent_device(tmp_path):
    path=tmp_path/'paysim.csv';path.write_text('step,type,amount,nameOrig,nameDest,isFraud\n1,TRANSFER,100,C1,C2,0\n')
    data=load_csv(path,'paysim')
    assert data.iloc[0].account_id=='C1'
    assert data.iloc[0].device_id is None
    assert data.iloc[0].synthetic

def test_banksim_excludes_demographic_features(tmp_path):
    path=tmp_path/'banksim.csv';path.write_text("step,customer,merchant,amount,fraud,age,gender\n1,'C1','M1',150,1,5,F\n")
    data=load_csv(path,'banksim')
    assert 'age' not in data and 'gender' not in data
    assert data.iloc[0].account_id=='C1'

def test_advanced_temporal_edges():
    torch=pytest.importorskip('torch')
    from backend.app.ml.advanced import temporal_edges
    data=generate(20);edges=temporal_edges(data)
    assert edges.shape[0]==2
    if edges.numel(): assert torch.all(edges[0]<edges[1])
