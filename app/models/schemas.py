from typing import List, Optional
from pydantic import BaseModel

class OCRRegion(BaseModel):
    text: str
    confidence: float
    bbox: List[int]
    engine: str
    risk_flags: List[str] = []

class PageAnalysis(BaseModel):
    page: int
    width: int
    height: int
    average_confidence: float
    difficulty: str
    risk_flags: List[str]
    regions: List[OCRRegion]

class JobResult(BaseModel):
    job_id: str
    status: str
    input_file: str
    output_pdf: Optional[str] = None
    evidence_json: Optional[str] = None
    pages: int = 0
    easy_pages: int = 0
    medium_pages: int = 0
    hard_pages: int = 0
    review_required: int = 0
    errors: List[str] = []
