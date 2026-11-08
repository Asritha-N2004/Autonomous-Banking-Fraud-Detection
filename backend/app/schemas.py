from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

Identifier = str

class TransactionInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    account_id: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    beneficiary_id: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    merchant_id: str | None = Field(default=None, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    device_id: str | None = Field(default=None, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    timestamp: datetime
    amount: float = Field(gt=0, le=1e10, allow_inf_nan=False)
    currency: str = Field(default='INR', pattern=r'^[A-Z]{3}$')
    transaction_type: Literal['transfer', 'purchase', 'withdrawal', 'deposit'] = 'transfer'
    channel: Literal['mobile', 'web', 'atm', 'branch'] = 'mobile'
    synthetic: bool = True
    historical_label: Literal[0, 1] | None = None
    source: str = Field(default='synthetic-generator-v1', min_length=1, max_length=100)

    @field_validator('timestamp')
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None: raise ValueError('timestamp must include timezone')
        return value.astimezone(timezone.utc)

class Login(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=256)

class UserInput(Login):
    role: Literal['ADMIN', 'FRAUD_INVESTIGATOR', 'ANALYST', 'AUDITOR', 'SUPERVISOR']

class Registration(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=256)
    confirm_password: str = Field(min_length=12, max_length=256)

    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self

class Analyze(BaseModel):
    transaction_id: str

class NoteInput(BaseModel):
    text: str = Field(min_length=1, max_length=10000)

class ReviewInput(BaseModel):
    outcome: Literal['confirmed_fraud', 'false_positive', 'inconclusive']
    rationale: str = Field(min_length=10, max_length=10000)
    decision: Literal['approve_recommendation', 'reject_recommendation', 'request_more_information']

class CaseUpdate(BaseModel):
    status: Literal['awaiting_review', 'in_progress'] | None = None
    assigned_to: str | None = None

class AgentResult(BaseModel):
    agent: str
    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    findings: list[str]
    references: list[str]
    provenance: str
    uncertainty: str
    details: dict = Field(default_factory=dict)

class SettingsInput(BaseModel):
    weights: dict[str, float]
    thresholds: dict[str, float]
    agent_retries: int = Field(ge=0, le=3)
    investigation_timeout_seconds: int = Field(ge=1, le=120)
    max_iterations: int = Field(ge=1, le=3)
    retention_days: int = Field(ge=30, le=3650)
    model: Literal['logistic_regression', 'random_forest', 'gradient_boosting']
    policy_version: str = Field(min_length=1, max_length=100)
