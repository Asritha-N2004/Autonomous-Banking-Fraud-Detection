from functools import lru_cache
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from ..config import MODEL_PATH

@lru_cache(maxsize=1)
def load_bundle(stamp=None):
    # Only trusted locally generated artifacts may be loaded; never upload joblib files.
    return joblib.load(MODEL_PATH)

def predict(features, model='random_forest'):
    predicted_at=datetime.now(timezone.utc).isoformat()
    if not MODEL_PATH.exists():
        return {'available':False,'fraud_probability':None,'anomaly_score':None,'model_version':None,'explanation':[], 'limitation':'Train models before inference'}
    bundle = load_bundle(MODEL_PATH.stat().st_mtime_ns)
    cutoff=pd.Timestamp(bundle['metadata']['split_end_times']['validation'])
    event_time=pd.Timestamp(features['timestamp'])
    if event_time<=cutoff:
        return {'available':False,'fraud_probability':None,'anomaly_score':None,'model_version':bundle['metadata']['version'],
            'prediction_timestamp':predicted_at,'explanation':[], 'limitation':'Temporal guard: event predates the model calibration cutoff. No hindsight prediction is used.',
            'calibration_cutoff':str(cutoff)}
    x = bundle['preprocessor'].transform(pd.DataFrame([features]))
    estimator = bundle['models'][model]
    probability = float(estimator.predict_proba(x)[0,1])
    raw = float(-bundle['isolation_forest'].score_samples(x)[0])
    percentile = float(np.searchsorted(bundle['anomaly_reference'],raw)/len(bundle['anomaly_reference']))
    # Local one-feature replacement sensitivity; not SHAP or causal attribution.
    names = bundle['preprocessor'].get_feature_names_out()
    explanations=[]
    for i,name in enumerate(names):
        changed=x.copy(); changed[0,i]=bundle['reference_median'][i]
        delta=probability-float(estimator.predict_proba(changed)[0,1])
        explanations.append({'feature':str(name),'probability_delta':round(delta,5)})
    explanations.sort(key=lambda d:abs(d['probability_delta']),reverse=True)
    return dict(available=True,fraud_probability=probability,anomaly_score=percentile,raw_anomaly_score=raw,
        prediction_timestamp=predicted_at,temporal_valid=True,calibration_cutoff=str(cutoff),
        model=model,model_version=bundle['metadata']['version'],explanation=explanations[:8],
        attribution_method='single-feature median replacement sensitivity; non-additive, non-causal',
        calibration_scope='sigmoid calibration on held-out synthetic temporal validation' if bundle['metadata']['synthetic'] else 'temporal validation')
