import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.database import Base,get_db,User,Role
from backend.app.main import app,requests_by_ip
from backend.app.security import hash_password,ROLES

@pytest.fixture
def client():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    from sqlalchemy import event
    @event.listens_for(engine,'connect')
    def fk(connection,_): connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine); factory=sessionmaker(engine,expire_on_commit=False)
    with factory() as db:
        for role in ROLES: db.add(Role(name=role))
        db.flush()
        for role in ROLES:
            db.add(User(id=role,username=role.lower(),role=role,password_hash=hash_password('Synthetic-Test-Password!')))
        db.commit()
    def override():
        with factory() as db: yield db
    app.dependency_overrides[get_db]=override
    requests_by_ip.clear()
    with TestClient(app) as test:
        test.db_factory=factory
        yield test
    app.dependency_overrides.clear(); engine.dispose()

@pytest.fixture
def admin(client):
    response=client.post('/api/auth/login',json={'username':'admin','password':'Synthetic-Test-Password!'})
    assert response.status_code==200
    return client
