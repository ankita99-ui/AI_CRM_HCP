from datetime import date, datetime

from pydantic import BaseModel, Field


class AttachmentPayload(BaseModel):
    file_name: str
    file_url: str


class InteractionCreate(BaseModel):
    doctor_name: str = Field(min_length=2)
    interaction_type: str
    discussion_notes: str = Field(min_length=10)
    products_discussed: list[str] = Field(default_factory=list)
    follow_up_date: date | None = None
    attachments: list[AttachmentPayload] = Field(default_factory=list)
    summary: str | None = None
    sentiment: str | None = 'neutral'


class InteractionUpdate(BaseModel):
    doctor_name: str | None = None
    interaction_type: str | None = None
    discussion_notes: str | None = None
    products_discussed: list[str] | None = None
    follow_up_date: date | None = None
    attachments: list[AttachmentPayload] | None = None
    summary: str | None = None
    sentiment: str | None = None
    status: str | None = None


class ExtractedInteraction(BaseModel):
    doctor_name: str = ''
    hospital: str = ''
    interaction_type: str = 'visit'
    interaction_date: date | None = None
    interaction_time: str | None = None
    discussion_notes: str = ''
    summary: str = ''
    products_discussed: list[str] = Field(default_factory=list)
    materials_shared: list[str] = Field(default_factory=list)
    follow_up_date: date | None = None
    follow_up_actions: str = ''
    sentiment: str | None = 'neutral'
    status: str = 'draft'


class InteractionRead(ExtractedInteraction):
    id: int
    hcp_id: int | None = None
    created_at: datetime
    updated_at: datetime
    attachments: list[AttachmentPayload] = []

    model_config = {'from_attributes': True}
