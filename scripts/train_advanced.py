import sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from backend.app.ml.advanced import run_advanced
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',default='data/synthetic/transactions.csv');p.add_argument('--epochs',type=int,default=35);a=p.parse_args()
    print(json.dumps(run_advanced(pd.read_csv(a.input),a.epochs),indent=2))
