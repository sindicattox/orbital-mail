from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, model_validator


class CampaignStatus(str, Enum):
    DRAFT = 'draft'
    READY = 'ready'
    SENDING = 'sending'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    ERROR = 'error'


class CampaignBase(BaseModel):
    internal_name: str = Field(min_length=2, max_length=255)
    subject: str = Field(min_length=2, max_length=500)
    body_html: str | None = None
    body_text: str | None = None
    sender_name: str = Field(min_length=2, max_length=255)
    sender_email: EmailStr
    reply_to: EmailStr | None = None

    @model_validator(mode='after')
    def validate_content(self):
        if not (self.body_html or '').strip() and not (self.body_text or '').strip():
            raise ValueError('Informe o conteúdo HTML ou o conteúdo em texto.')
        return self


class CampaignCreate(CampaignBase):
    status: CampaignStatus = CampaignStatus.DRAFT


class CampaignUpdate(CampaignBase):
    status: CampaignStatus = CampaignStatus.DRAFT


class CampaignSummary(BaseModel):
    id: int
    internal_name: str
    subject: str
    sender_name: str | None = None
    sender_email: str | None = None
    reply_to: str | None = None
    status: str
    send_date: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CampaignDetail(CampaignSummary):
    body_html: str | None = None
    body_text: str | None = None


class QueuePrepareStart(BaseModel):
    associative_code: str | None = Field(default=None, max_length=30)
    functional_code: str | None = Field(default=None, max_length=30)
    profile_code: str | None = Field(default=None, max_length=64)
    test_email: EmailStr | None = None


class QueuePrepareBatch(QueuePrepareStart):
    cutoff: datetime
    target_total: int = Field(ge=0)
    batch_size: int = Field(default=250, ge=10, le=1000)
