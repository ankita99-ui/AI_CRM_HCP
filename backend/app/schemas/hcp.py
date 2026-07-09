from datetime import datetime

from pydantic import BaseModel, EmailStr


class HCPBase(BaseModel):
    doctor_name: str
    hospital: str
    speciality: str
    city: str | None = None
    email: EmailStr | None = None
    history_summary: str | None = None


class HCPRead(HCPBase):
    id: int
    last_visit: datetime | None = None
    recent_products: list[str] = []

    model_config = {'from_attributes': True}
