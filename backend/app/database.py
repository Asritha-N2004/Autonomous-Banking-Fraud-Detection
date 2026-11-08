from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, Float, Integer, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATABASE_URL

def now():
    return datetime.now(timezone.utc).isoformat()

def uid():
    return str(uuid4())

engine_options={'connect_args':{'check_same_thread':False}} if DATABASE_URL.startswith('sqlite') else {'pool_pre_ping':True}
if __import__('os').getenv('VERCEL')=='1':
    from sqlalchemy.pool import NullPool
    engine_options['poolclass']=NullPool
engine = create_engine(DATABASE_URL, **engine_options)
if DATABASE_URL.startswith('sqlite'):
    from sqlalchemy import event
    @event.listens_for(engine, 'connect')
    def foreign_keys(dbapi_connection, _):
        dbapi_connection.execute('PRAGMA foreign_keys=ON')
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class Role(Base):
    __tablename__ = 'roles'
    name: Mapped[str] = mapped_column(String(40), primary_key=True)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(ForeignKey('roles.name'))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class SessionToken(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[str] = mapped_column(String(50))

class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

class Account(Base):
    __tablename__ = 'accounts'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'))

class Merchant(Base):
    __tablename__ = 'merchants'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

class Beneficiary(Base):
    __tablename__ = 'beneficiaries'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

class Device(Base):
    __tablename__ = 'devices'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey('accounts.id'), index=True)
    beneficiary_id: Mapped[str] = mapped_column(ForeignKey('beneficiaries.id'), index=True)
    merchant_id: Mapped[str | None] = mapped_column(ForeignKey('merchants.id'), nullable=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey('devices.id'), nullable=True)
    timestamp: Mapped[str] = mapped_column(String(50), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default='INR')
    transaction_type: Mapped[str] = mapped_column(String(30))
    channel: Mapped[str] = mapped_column(String(30))
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    historical_label: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(100), default='synthetic-generator-v1')

class Investigation(Base):
    __tablename__ = 'investigations'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    transaction_id: Mapped[str] = mapped_column(ForeignKey('transactions.id'), index=True)
    assigned_to: Mapped[str] = mapped_column(ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String(40), default='awaiting_review')
    priority: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(20))
    report: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(50), default=now)
    updated_at: Mapped[str] = mapped_column(String(50), default=now)
    review: Mapped[dict | None] = mapped_column(JSON, nullable=True)

class Alert(Base):
    __tablename__ = 'fraud_alerts'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    transaction_id: Mapped[str] = mapped_column(ForeignKey('transactions.id'), index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey('investigations.id'))
    priority: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40), default='unverified')

class Evidence(Base):
    __tablename__ = 'evidence'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('investigations.id'), index=True)
    payload: Mapped[dict] = mapped_column(JSON)

class Note(Base):
    __tablename__ = 'investigation_notes'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('investigations.id'))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    text: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[str] = mapped_column(String(50), default=now)

class AgentRun(Base):
    __tablename__ = 'agent_runs'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    case_id: Mapped[str | None] = mapped_column(ForeignKey('investigations.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[str] = mapped_column(String(50), default=now)
    duration_ms: Mapped[float] = mapped_column(Float)

class AgentLog(Base):
    __tablename__ = 'agent_logs'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey('agent_runs.id'), index=True)
    agent: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON)

class Prediction(Base):
    __tablename__ = 'model_predictions'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    transaction_id: Mapped[str] = mapped_column(ForeignKey('transactions.id'))
    payload: Mapped[dict] = mapped_column(JSON)

class ModelVersion(Base):
    __tablename__ = 'model_versions'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)

class ModelMetric(Base):
    __tablename__ = 'model_metrics'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    model_version: Mapped[str] = mapped_column(ForeignKey('model_versions.id'))
    payload: Mapped[dict] = mapped_column(JSON)

class GraphEntity(Base):
    __tablename__ = 'graph_entities'
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)

class GraphRelationship(Base):
    __tablename__ = 'graph_relationships'
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('graph_entities.id'))
    target_id: Mapped[str] = mapped_column(ForeignKey('graph_entities.id'))
    payload: Mapped[dict] = mapped_column(JSON)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    timestamp: Mapped[str] = mapped_column(String(50), default=now)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

class Setting(Base):
    __tablename__ = 'system_settings'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)

def init_db():
    if __import__('os').getenv('VERCEL')=='1':
        if not DATABASE_URL.startswith('postgresql+psycopg://'):
            raise RuntimeError('Vercel requires a persistent PostgreSQL DATABASE_URL; local SQLite is not a hosted database.')
        from sqlalchemy import text
        with engine.begin() as connection:
            connection.execute(text('SELECT pg_advisory_xact_lock(682143900)'))
            Base.metadata.create_all(connection)
    else:
        Base.metadata.create_all(engine)

def get_db():
    with SessionLocal() as db:
        yield db
