"""
AI Interview Pilot — FastAPI Backend (Fixed)
"""

import os
import uuid
import logging

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends, HTTPException

from app.auth import create_access_token
from app.config import settings



from sqlalchemy.orm import Session
from jose import JWTError, jwt
from pypdf import PdfReader
from typing import List

from app.config import settings
from app.db.database import Base, engine, get_db  # ✅ engine comes from database.py ONLY

from app.models.user import User
from app.models.resume import Resume
from app.models.interview import InterviewHistory
from app.models.evaluation import Evaluation
from app.models.analysis import ResumeAnalysis

from app.schemas.user import UserCreate, UserResponse
from app.schemas.interview import (
    AskRequest,
    InterviewHistoryResponse,
    EvaluateRequest,
    EvaluateResponse,
    ResumeAnalysisResponse,
    DashboardResponse,
)
from app.schemas.schemas import LoginRequest,UserCreate, UserResponse
from app.schemas.user import UserCreate, UserResponse

from app.security import hash_password, verify_password  # ✅ ONE import only
from app.auth import create_access_token
# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title=settings.APP_NAME)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# ✅ Create tables on startup (needed for Neon fresh DB)
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# 422 Error logger — shows exactly what field failed
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):

    body = await request.body()

    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "body": body.decode(errors="replace")
        },
    )

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)




# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def home():
    return {"message": "AI Interview Pilot API — Running ✅"}


# ── Auth ──────────────────────────────────────────────────────────────────

@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = User(
        email=user.email,
        full_name=user.full_name,
        password=hash_password(user.password),  # ✅ stores as "password" field
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user



@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email")

    # ✅ Use verify_password instead of direct comparison
    if not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials"
    )

    try:

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        email = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(
        User.email == email
    ).first()

    if user is None:
        raise credentials_exception

    return user


@app.get("/me")
def read_users_me(
    current_user: User = Depends(get_current_user)
):

    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email
    }

# ── Resume ────────────────────────────────────────────────────────────────

@app.post("/upload-resume")
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_location, "wb") as buffer:
        buffer.write(file.file.read())

    reader = PdfReader(file_location)
    text = "".join(
        page.extract_text() + "\n" for page in reader.pages if page.extract_text()
    )

    resume = Resume(
        file_name=unique_filename,
        file_path=file_location,
        resume_text=text,
        user_id=current_user.id,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {"message": "Resume uploaded & parsed successfully", "resume_id": resume.id}


@app.get("/my-resumes")
def get_my_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Resume).filter(Resume.user_id == current_user.id).all()


# ── Interview ─────────────────────────────────────────────────────────────

@app.post("/ask")
def ask_interview_question(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.ai_service import ask_resume_question

    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found. Upload resume first.")
    if not resume.resume_text:
        raise HTTPException(status_code=400, detail="Resume text not extracted.")

    answer = ask_resume_question(resume.resume_text, request.question)

    history = InterviewHistory(
        question=request.question, answer=answer, user_id=current_user.id
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return {"question": request.question, "answer": answer, "history_id": history.id}


@app.get("/history", response_model=List[InterviewHistoryResponse])
def get_interview_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
):
    return (
        db.query(InterviewHistory)
        .filter(InterviewHistory.user_id == current_user.id)
        .order_by(InterviewHistory.created_at.desc())
        .limit(limit)
        .all()
    )


# ── Evaluation ────────────────────────────────────────────────────────────

@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate_interview_answer(
    request: EvaluateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.ai_service import evaluate_answer

    result = evaluate_answer(request.question, request.user_answer)

    evaluation = Evaluation(
        question=request.question,
        user_answer=request.user_answer,
        score=result["score"],
        technical_feedback=result["technical_feedback"],
        improvements=result["improvements"],
        user_id=current_user.id,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


@app.get("/weak-areas")
def get_weak_areas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.ai_service import generate_weak_area_summary

    evaluations = (
        db.query(Evaluation).filter(Evaluation.user_id == current_user.id).all()
    )
    if not evaluations:
        return {"message": "No evaluations found."}

    average_score = round(sum(e.score for e in evaluations) / len(evaluations), 2)
    weak_topics = [e.question for e in evaluations if e.score <= 6]
    recommendation = generate_weak_area_summary(weak_topics, average_score) if weak_topics else None

    return {
        "average_score": average_score,
        "weak_topics": weak_topics,
        "total_attempts": len(evaluations),
        "recommendation": recommendation,
    }


# ── Resume Analysis ───────────────────────────────────────────────────────

@app.post("/analyze-resume", response_model=ResumeAnalysisResponse)
def analyze_user_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.ai_service import analyze_resume

    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")

    result = analyze_resume(resume.resume_text)

    analysis = ResumeAnalysis(
        ats_score=result["ats_score"],
        strengths=", ".join(result["strengths"]),
        missing_skills=", ".join(result["missing_skills"]),
        improvements=", ".join(result["improvements"]),
        user_id=current_user.id,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "ats_score": analysis.ats_score,
        "strengths": result["strengths"],
        "missing_skills": result["missing_skills"],
        "improvements": result["improvements"],
        "created_at": analysis.created_at,
    }


# ── Dashboard ─────────────────────────────────────────────────────────────

@app.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.ai_service import generate_weak_area_summary

    evaluations = (
        db.query(Evaluation).filter(Evaluation.user_id == current_user.id).all()
    )

    if evaluations:
        average_score = round(sum(e.score for e in evaluations) / len(evaluations), 2)
        weak_topics = [e.question for e in evaluations if e.score <= 6]
        recommendation = generate_weak_area_summary(weak_topics, average_score) if weak_topics else None
    else:
        average_score, weak_topics, recommendation = 0, [], None

    latest_analysis = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == current_user.id)
        .order_by(ResumeAnalysis.created_at.desc())
        .first()
    )

    return {
        "average_score": average_score,
        "total_interviews": len(evaluations),
        "weak_topics": weak_topics,
        "ats_score": latest_analysis.ats_score if latest_analysis else None,
        "recommendation": recommendation,
    }