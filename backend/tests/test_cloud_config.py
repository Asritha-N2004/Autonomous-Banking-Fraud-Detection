import pytest
from backend.app.config import allowed_origins
from backend.app import database

def test_hosted_cookie_origins_are_exact_deployment_hosts(monkeypatch):
    monkeypatch.setenv('VERCEL','1');monkeypatch.delenv('CORS_ORIGINS',raising=False)
    monkeypatch.setenv('VERCEL_URL','synthetic-preview.vercel.app')
    monkeypatch.setenv('VERCEL_PROJECT_PRODUCTION_URL','synthetic-production.vercel.app')
    assert allowed_origins()==['https://synthetic-preview.vercel.app','https://synthetic-production.vercel.app']
    assert 'https://untrusted.vercel.app' not in allowed_origins()

def test_hosted_startup_refuses_ephemeral_sqlite(monkeypatch):
    monkeypatch.setenv('VERCEL','1');monkeypatch.setattr(database,'DATABASE_URL','sqlite:///./synthetic.db')
    with pytest.raises(RuntimeError,match='persistent PostgreSQL'):
        database.init_db()
