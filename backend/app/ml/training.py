import hashlib
import importlib.metadata
import json
from datetime import datetime, timezone
import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix
from .features import FEATURES, CATEGORICAL, engineer
from ..config import MODEL_PATH

def evaluate(y, p):
    predicted = p >= .5
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0,1]).ravel()
    k = max(1, int(len(y)*.05))
    top = np.argsort(p)[-k:]
    return dict(precision=float(precision_score(y,predicted,zero_division=0)), recall=float(recall_score(y,predicted,zero_division=0)),
        f1=float(f1_score(y,predicted,zero_division=0)), roc_auc=float(roc_auc_score(y,p)) if len(set(y))>1 else None,
        pr_auc=float(average_precision_score(y,p)) if sum(y)>0 else None,
        precision_at_k=float(np.mean(np.asarray(y)[top])), recall_at_k=float(np.sum(np.asarray(y)[top])/max(sum(y),1)), k=k,
        confusion_matrix=[[int(tn),int(fp)],[int(fn),int(tp)]], false_positive_rate=float(fp/max(tn+fp,1)),
        false_negative_rate=float(fn/max(tp+fn,1)), samples=len(y), positive_labels=int(sum(y)))

def train(frame, path=MODEL_PATH):
    data = engineer(frame)
    if len(data)<200: raise ValueError('At least 200 labeled transactions required')
    if data['historical_label'].isna().any(): raise ValueError('Training requires verified or explicitly synthetic labels')
    a,b = int(len(data)*.6),int(len(data)*.8)
    # Do not split equal-timestamp event groups across temporal partitions.
    while a<len(data) and data.iloc[a].timestamp==data.iloc[a-1].timestamp: a+=1
    b=max(b,a+1)
    while b<len(data) and data.iloc[b].timestamp==data.iloc[b-1].timestamp: b+=1
    train_data, validation, test = data.iloc[:a], data.iloc[a:b], data.iloc[b:]
    for split in [train_data,validation,test]:
        if split.historical_label.nunique()<2: raise ValueError('Each temporal split needs both classes')
    numeric = Pipeline([('missing',SimpleImputer(strategy='median')),('scale',StandardScaler())])
    pre = ColumnTransformer([('num',numeric,FEATURES),('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),CATEGORICAL)])
    x = pre.fit_transform(train_data)
    xv, xt = pre.transform(validation),pre.transform(test)
    y,yv,yt = [s.historical_label.astype(int).to_numpy() for s in [train_data,validation,test]]
    estimators = {'logistic_regression':LogisticRegression(class_weight='balanced',max_iter=500,random_state=42),
        'random_forest':RandomForestClassifier(n_estimators=100,max_depth=8,class_weight='balanced',random_state=42,n_jobs=1),
        'gradient_boosting':GradientBoostingClassifier(n_estimators=80,max_depth=2,random_state=42)}
    try:
        from xgboost import XGBClassifier
        estimators['xgboost']=XGBClassifier(n_estimators=80,max_depth=3,learning_rate=.08,scale_pos_weight=float((y==0).sum()/max((y==1).sum(),1)),random_state=42,n_jobs=1,eval_metric='logloss')
    except ImportError:
        pass  # Optional dependency: the three required classical baselines remain available.
    models,metrics = {},{}
    for name, model in estimators.items():
        model.fit(x,y)
        calibrated = CalibratedClassifierCV(FrozenEstimator(model),method='sigmoid')
        calibrated.fit(xv,yv)
        models[name] = calibrated
        metrics[name] = evaluate(yt,calibrated.predict_proba(xt)[:,1])
    anomaly = IsolationForest(n_estimators=100,contamination='auto',random_state=42).fit(x)
    lof = LocalOutlierFactor(n_neighbors=20,novelty=True).fit(x)
    # Anomaly metrics use rankings, never a probability interpretation.
    for name, estimator in [('isolation_forest',anomaly),('local_outlier_factor',lof)]:
        score = -estimator.score_samples(xt)
        metrics[name] = {'pr_auc':float(average_precision_score(yt,score)), 'roc_auc':float(roc_auc_score(yt,score)), 'score_type':'uncalibrated_anomaly_ranking', 'samples':len(yt)}
    fingerprint = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
    runtime={name:importlib.metadata.version(name) for name in ['scikit-learn','numpy','pandas','networkx','joblib']}
    configuration={'seed':42,'train_fraction':.6,'validation_fraction':.2,'calibration':'sigmoid','features':FEATURES+CATEGORICAL,'estimators':list(models)}
    version = 'baseline-' + hashlib.sha256(json.dumps({'data':fingerprint,'runtime':runtime,'configuration':configuration},sort_keys=True).encode()).hexdigest()[:12]
    metadata = dict(version=version, seed=42, data_sha256=fingerprint, created_at=datetime.now(timezone.utc).isoformat(),
        synthetic=bool(frame.synthetic.all()), runtime=runtime,configuration=configuration,splits={'train':a,'validation':b-a,'test':len(data)-b},
        split_end_times={name:str(split.timestamp.max()) for name,split in [('train',train_data),('validation',validation),('test',test)]},
        train_positive_rate=float(y.mean()), metrics=metrics,
        limitations=['Synthetic benchmark only; no banking validity established.', 'Calibration measured on synthetic temporal validation; real-world recalibration required.', 'Channel subgroup metrics are operational, not protected-attribute fairness certification.'],
        channel_subgroups={str(channel):evaluate(sub.historical_label.to_numpy(),models['random_forest'].predict_proba(pre.transform(sub))[:,1]) for channel,sub in test.groupby('channel')})
    bundle = dict(preprocessor=pre, models=models, isolation_forest=anomaly, local_outlier_factor=lof,
        anomaly_reference=np.sort(-anomaly.score_samples(x)), reference_median=np.median(x,axis=0),metadata=metadata)
    path.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(bundle,path)
    path.with_suffix('.json').write_text(json.dumps(metadata,indent=2))
    return metadata
