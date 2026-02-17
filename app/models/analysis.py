from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"

    id = Column(Integer, primary_key=True, index=True)

    ats_score = Column(Integer, nullable=False)
    strengths = Column(Text, nullable=False)
    missing_skills = Column(Text, nullable=False)
    improvements = Column(Text, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
