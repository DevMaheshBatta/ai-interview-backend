from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)

    question = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=False)

    score = Column(Integer, nullable=False)
    technical_feedback = Column(Text, nullable=False)
    improvements = Column(Text, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
