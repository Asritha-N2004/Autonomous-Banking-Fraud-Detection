"""Build trusted synthetic model artifacts without uploading local data or credentials."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.ml.data import generate
from backend.app.ml.training import train

if __name__=='__main__':
    metadata=train(generate(n=2400,seed=42))
    print(f"Built synthetic models: {metadata['version']}; no local database or users included.")
