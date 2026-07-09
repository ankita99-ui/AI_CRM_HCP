from pydantic import BaseModel


class EmailRequest(BaseModel):
    doctor_name: str
    summary: str
    products_discussed: list[str]
    call_to_action: str


class EmailResponse(BaseModel):
    subject: str
    body: str
