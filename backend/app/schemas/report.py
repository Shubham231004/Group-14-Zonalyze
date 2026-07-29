from pydantic import BaseModel


class FeasibilityReportResponse(BaseModel):
    filename: str
    content_type: str = "text/plain"
    report_text: str
