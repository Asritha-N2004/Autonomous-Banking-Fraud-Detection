from sqlalchemy import select
from backend.app.database import User,AuditLog
from backend.app.security import verify_password

def registration(username='synthetic-new-analyst'):
    return {'username':username,'password':'Synthetic-Account-Password!','confirm_password':'Synthetic-Account-Password!'}

def test_registration_creates_hashed_analyst_and_session(client):
    response=client.post('/api/auth/register',json=registration())
    assert response.status_code==201,response.text
    user=response.json()['user']
    assert user['role']=='ANALYST'
    assert 'httponly' in response.headers['set-cookie'].lower()
    assert client.get('/api/auth/me').json()['id']==user['id']
    assert client.get('/api/analytics/dashboard').status_code==200
    assert client.get('/api/settings').status_code==403
    assert client.post('/api/fraud/analyze',json={'transaction_id':'missing'}).status_code==403
    with client.db_factory() as db:
        stored=db.get(User,user['id'])
        assert stored.password_hash!=registration()['password']
        assert verify_password(registration()['password'],stored.password_hash)
        assert db.scalar(select(AuditLog).where(AuditLog.action=='self_register')).entity_id==user['id']
    client.post('/api/auth/logout')
    assert client.post('/api/auth/login',json={'username':user['username'],'password':registration()['password']}).status_code==200

def test_registration_duplicate_is_case_insensitive(client):
    assert client.post('/api/auth/register',json=registration('  Synthetic.User  ')).status_code==201
    assert client.get('/api/auth/me').json()['username']=='synthetic.user'
    assert client.post('/api/auth/register',json=registration('SYNTHETIC.USER')).status_code==409
    assert client.post('/api/auth/register',json=registration('ADMIN')).status_code==409

def test_registration_cannot_select_privileged_role(client):
    payload={**registration(),'role':'ADMIN'}
    assert client.post('/api/auth/register',json=payload).status_code==422
    with client.db_factory() as db:
        assert db.scalar(select(User).where(User.username==payload['username'])) is None

def test_registration_rejects_invalid_credentials(client):
    payload=registration();payload['confirm_password']='A-Different-Password!'
    assert client.post('/api/auth/register',json=payload).status_code==422
    payload=registration();payload['password']=payload['confirm_password']='short'
    assert client.post('/api/auth/register',json=payload).status_code==422
    assert client.post('/api/auth/register',json=registration('   ')).status_code==422

def test_registration_accepts_simple_names_emails_and_unicode(client):
    for username in ['A', 'Synthetic Full Name', 'synthetic@example.test', 'Test User + 1', 'Synthetíc User']:
        response=client.post('/api/auth/register',json=registration(username))
        assert response.status_code==201,response.text
        assert response.json()['user']['username']==username.lower()
        client.post('/api/auth/logout')
        assert client.post('/api/auth/login',json={'username':'  '+username+'  ','password':registration()['password']}).status_code==200
    assert client.post('/api/auth/register',json=registration('SYNTHETIC FULL NAME')).status_code==409

def test_registration_and_login_share_rate_limit(client):
    for _ in range(20):
        assert client.post('/api/auth/login',json={'username':'missing','password':'invalid'}).status_code==401
    assert client.post('/api/auth/register',json=registration()).status_code==429
