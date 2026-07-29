from pydantic import BaseModel


class ValidationCheck(BaseModel):
    name: str
    status: str
    message: str


class SystemValidationResponse(BaseModel):
    overall_status: str
    passed_checks: int
    total_checks: int
    checks: list[ValidationCheck]
