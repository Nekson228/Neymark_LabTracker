from typing import List, Optional
from datetime import datetime, timedelta

from pydantic import BaseModel, Field


class AnalysisScan(BaseModel):
    user_id: int
    file_id: str
    uploaded_at: datetime
    recognized_text: Optional[str] = None


class AnalysisResult(BaseModel):
    user_id: int
    summary: str
    generated_at: datetime


class AnalysisHistory(BaseModel):
    user_id: int
    analyses: list[AnalysisResult]


class AnalysesQuery(BaseModel):
    user_id: int
    since: timedelta
