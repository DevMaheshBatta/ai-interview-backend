from pydantic import BaseModel
from datetime import datetime

class AskRequest(BaseModel):
    question: str
class InterviewHistoryResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime

    class Config:
        orm_mode = True
class EvaluateRequest(BaseModel):
    question: str
    user_answer: str


class EvaluateResponse(BaseModel):
    score: int
    technical_feedback: str
    improvements: str
    created_at: datetime

    class Config:
        orm_mode = True
from typing import List

class ResumeAnalysisResponse(BaseModel):
    ats_score: int
    strengths: List[str]
    missing_skills: List[str]
    improvements: List[str]
    created_at: datetime

    class Config:
        orm_mode = True
class DashboardResponse(BaseModel):
    average_score: float
    total_interviews: int
    weak_topics: list[str]
    ats_score: int | None
    recommendation: str | None

    class Config:
        orm_mode = True
