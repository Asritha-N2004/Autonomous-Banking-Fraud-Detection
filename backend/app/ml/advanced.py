"""Optional real PyTorch autoencoder and PyG temporal transaction GraphSAGE experiment.

No graph contains future edges. One node per transaction; edges connect consecutive
observations on an account/device. Labels are masked to the training interval.
"""
import json
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, roc_auc_score
from .features import engineer,FEATURES
from .training import evaluate
from ..config import ROOT

class Autoencoder(nn.Module):
    def __init__(self,width):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(width,16),nn.ReLU(),nn.Linear(16,4),nn.ReLU(),nn.Linear(4,16),nn.ReLU(),nn.Linear(16,width))
    def forward(self,x): return self.net(x)

def temporal_edges(data):
    last={};edges=[]
    for i,t in enumerate(data.to_dict('records')):
        for field in ['account_id','device_id']:
            value=t.get(field)
            if value is None: continue
            key=(field,value)
            if key in last: edges.append((last[key],i))
            last[key]=i
    return torch.tensor(edges,dtype=torch.long).T.contiguous() if edges else torch.empty((2,0),dtype=torch.long)

def run_advanced(frame,epochs=35):
    from torch_geometric.nn import SAGEConv
    torch.manual_seed(42); np.random.seed(42); torch.set_num_threads(1)
    data=engineer(frame); a,b=int(len(data)*.6),int(len(data)*.8)
    scaler=StandardScaler().fit(data.iloc[:a][FEATURES])
    x=torch.tensor(scaler.transform(data[FEATURES]),dtype=torch.float32)
    y=torch.tensor(data.historical_label.to_numpy(),dtype=torch.float32)
    ae=Autoencoder(x.shape[1]); optimizer=torch.optim.Adam(ae.parameters(),lr=.005)
    normal=x[:a][y[:a]==0]
    for _ in range(epochs):
        optimizer.zero_grad();loss=((ae(normal)-normal)**2).mean();loss.backward();optimizer.step()
    ae.eval()
    with torch.no_grad(): scores=((ae(x[b:])-x[b:])**2).mean(dim=1).numpy()
    results={'autoencoder':{'pr_auc':float(average_precision_score(y[b:].numpy(),scores)),
        'roc_auc':float(roc_auc_score(y[b:].numpy(),scores)),'score_type':'reconstruction_error; not probability'}}
    class GraphSAGE(nn.Module):
        def __init__(self,width):
            super().__init__();self.conv1=SAGEConv(width,24);self.conv2=SAGEConv(24,1)
        def forward(self,x,edges): return self.conv2(torch.relu(self.conv1(x,edges)),edges).flatten()
    graph=GraphSAGE(x.shape[1]); optimizer=torch.optim.Adam(graph.parameters(),lr=.01,weight_decay=1e-4)
    train_edges=temporal_edges(data.iloc[:a])
    criterion=nn.BCEWithLogitsLoss(pos_weight=torch.tensor(float((y[:a]==0).sum()/max((y[:a]==1).sum(),1))))
    for _ in range(epochs):
        graph.train();optimizer.zero_grad();loss=criterion(graph(x[:a],train_edges),y[:a]);loss.backward();optimizer.step()
    # Sigmoid calibrator fitted on later validation logits; test labels never train either model.
    from sklearn.linear_model import LogisticRegression
    graph.eval()
    with torch.no_grad():
        val_logits=graph(x[:b],temporal_edges(data.iloc[:b]))[a:b].numpy()
        test_logits=graph(x,temporal_edges(data))[b:].numpy()
    calibration=LogisticRegression(random_state=42).fit(val_logits.reshape(-1,1),y[a:b].numpy())
    probabilities=calibration.predict_proba(test_logits.reshape(-1,1))[:,1]
    results['graphsage']=evaluate(y[b:].numpy().astype(int),probabilities)
    metadata={'seed':42,'epochs':epochs,'synthetic':bool(frame.synthetic.all()),'models':results,'runtime':{'torch':torch.__version__,'torch_geometric':__import__('torch_geometric').__version__},
        'graph':'Directed temporal links from earlier to later transactions sharing account/device. Inference messages flow forward only.',
        'limitations':['Separate offline experiment; not the default API model.','Single synthetic seed; no real banking claims.','No future edges or labels used for training.']}
    target=ROOT/'models/advanced.pt'; torch.save({'autoencoder':ae.state_dict(),'graphsage':graph.state_dict(),'features':FEATURES,'scaler_mean':scaler.mean_.tolist(),'scaler_scale':scaler.scale_.tolist(),
        'calibration_coefficient':calibration.coef_.tolist(),'calibration_intercept':calibration.intercept_.tolist(),'metadata':metadata},target)
    (ROOT/'models/advanced.json').write_text(json.dumps(metadata,indent=2));return metadata
