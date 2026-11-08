import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Minimal dotenv reader: literal values only; never evaluate shell expressions.
if (ROOT / '.env').exists():
    for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('\"').strip("'"))
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{ROOT / "banking.db"}')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL=DATABASE_URL.replace('postgres://','postgresql+psycopg://',1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL=DATABASE_URL.replace('postgresql://','postgresql+psycopg://',1)
MODEL_PATH = Path(os.getenv('MODEL_PATH', str(ROOT / 'models/baselines.joblib')))

def allowed_origins():
    default='' if os.getenv('VERCEL')=='1' else 'http://localhost:5173'
    origins=[origin.strip() for origin in os.getenv('CORS_ORIGINS',default).split(',') if origin.strip()]
    if os.getenv('VERCEL')=='1':
        for key in ['VERCEL_URL','VERCEL_PROJECT_PRODUCTION_URL']:
            host=os.getenv(key,'').strip()
            if host and '/' not in host and '*' not in host:
                origins.append('https://'+host)
    return list(dict.fromkeys(origins))
POLICY_VERSION = 'research-v1'
DEFAULT_SETTINGS = {
    'weights': {'transaction': .16, 'behavioral': .18, 'account': .12, 'graph': .16, 'ml': .28, 'pattern': .10},
    'thresholds': {'medium': 30, 'high': 55, 'critical': 75},
    'agent_retries': 1, 'investigation_timeout_seconds': 30, 'max_iterations': 2,
    'retention_days': 365, 'model': 'random_forest', 'policy_version': POLICY_VERSION,
}
