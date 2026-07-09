from pydantic import BaseModel


class NextActionRequest(BaseModel):
    doctor_name: str
    products_discussed: list[str] = []
    summary: str = ''


class NextActionResponse(BaseModel):
    recommendations: list[str]
