from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import Base, engine, get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserLogin

from app.security import hash_password, verify_password
from fastapi import HTTPException

from app.auth import create_access_token
from app.core.security import hash_password
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi import UploadFile, File
import shutil
import os
from app.models.resume import Resume
import uuid
from pypdf import PdfReader
from app.services.ai_service import ask_resume_question
from app.models.interview import InterviewHistory
from app.schemas.interview import AskRequest
from app.services.ai_service import ask_resume_question

from typing import List
from app.models.interview import InterviewHistory
from app.schemas.interview import InterviewHistoryResponse
from app.models.evaluation import Evaluation
from app.schemas.interview import EvaluateRequest, EvaluateResponse
from app.services.ai_service import evaluate_answer
from app.models.evaluation import Evaluation
from sqlalchemy import func
from app.models.evaluation import Evaluation
from app.services.ai_service import generate_weak_area_summary
from app.schemas.interview import ResumeAnalysisResponse


from app.services.ai_service import analyze_resume
from app.models.resume import Resume

from app.models.analysis import ResumeAnalysis
from app.models.evaluation import Evaluation
from app.models.analysis import ResumeAnalysis
from app.services.ai_service import generate_weak_area_summary
from app.schemas.interview import DashboardResponse


from fastapi.middleware.cors import CORSMiddleware




oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Base.metadata.create_all(bind=engine)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
    token,
    settings.SECRET_KEY,
    algorithms=[settings.ALGORITHM]
)
        email: str = payload.get("sub")
        
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@app.get("/")
def home():
    return {"message": "Backend Running with DB"}


@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    
    # Simple hash (temporary — we improve later)
    hashed_password = hash_password(user.password)


    db_user = User(
        email=user.email,
        full_name=user.full_name,
        password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user






@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Query raw User object from DB
    db_user = db.query(User).filter(User.email == form_data.username).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # ✅ Access password column directly from SQLAlchemy object
    if not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": db_user.email})

    return {"access_token": access_token, "token_type": "bearer"}



@app.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user



@app.post("/upload-resume")
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file
    with open(file_location, "wb") as buffer:
        buffer.write(file.file.read())

    # 🔥 STEP 3 — Extract Text From PDF
    reader = PdfReader(file_location)
    text = ""

    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    # Store in DB
    resume = Resume(
        file_name=unique_filename,
        file_path=file_location,
        resume_text=text,  # 👈 STORE TEXT
        user_id=current_user.id
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "message": "Resume uploaded & parsed successfully",
        "resume_id": resume.id
    }






@app.get("/my-resumes")
def get_my_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resumes = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).all()

    return resumes




@app.post("/ask")
def ask_interview_question(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # 1️⃣ Get latest resume of user
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

    # 2️⃣ Call Gemini
    answer = ask_resume_question(resume.resume_text, request.question)

    # 3️⃣ Save Interview History
    history = InterviewHistory(
        question=request.question,
        answer=answer,
        user_id=current_user.id
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    # 4️⃣ Return Response
    return {
        "question": request.question,
        "answer": answer,
        "history_id": history.id
    }
@app.get("/history", response_model=List[InterviewHistoryResponse])
def get_interview_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    history = (
        db.query(InterviewHistory)
        .filter(InterviewHistory.user_id == current_user.id)
        .order_by(InterviewHistory.created_at.desc())
        .limit(limit)
        .all()
    )

    return history
@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate_interview_answer(
    request: EvaluateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    result = evaluate_answer(request.question, request.user_answer)

    evaluation = Evaluation(
        question=request.question,
        user_answer=request.user_answer,
        score=result["score"],
        technical_feedback=result["technical_feedback"],
        improvements=result["improvements"],
        user_id=current_user.id
    )

    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    return evaluation
@app.get("/weak-areas")
def get_weak_areas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    evaluations = (
        db.query(Evaluation)
        .filter(Evaluation.user_id == current_user.id)
        .all()
    )

    if not evaluations:
        return {"message": "No evaluations found."}

    total_score = 0
    weak_topics = []

    for eval in evaluations:
        total_score += eval.score

        if eval.score <= 6:
            weak_topics.append(eval.question)

    
    average_score = round(total_score / len(evaluations), 2)

    recommendation = None
    if weak_topics:
        recommendation = generate_weak_area_summary(weak_topics, average_score)

    return {
        "average_score": average_score,
        "weak_topics": weak_topics,
        "total_attempts": len(evaluations),
        "recommendation": recommendation
    }



@app.post("/analyze-resume", response_model=ResumeAnalysisResponse)
def analyze_user_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )

    if not resume:
        return {"error": "No resume found"}

    result = analyze_resume(resume.resume_text)

    analysis = ResumeAnalysis(
        ats_score=result["ats_score"],
        strengths=", ".join(result["strengths"]),
        missing_skills=", ".join(result["missing_skills"]),
        improvements=", ".join(result["improvements"]),
        user_id=current_user.id
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "ats_score": analysis.ats_score,
        "strengths": result["strengths"],
        "missing_skills": result["missing_skills"],
        "improvements": result["improvements"],
        "created_at": analysis.created_at
    }
@app.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # --- Interview Data ---
    evaluations = (
        db.query(Evaluation)
        .filter(Evaluation.user_id == current_user.id)
        .all()
    )

    if evaluations:
        total_score = sum(e.score for e in evaluations)
        average_score = round(total_score / len(evaluations), 2)

        weak_topics = [e.question for e in evaluations if e.score <= 6]

        recommendation = None
        if weak_topics:
            recommendation = generate_weak_area_summary(
                weak_topics,
                average_score
            )
    else:
        average_score = 0
        weak_topics = []
        recommendation = None

    # --- ATS Data ---
    latest_analysis = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == current_user.id)
        .order_by(ResumeAnalysis.created_at.desc())
        .first()
    )

    ats_score = latest_analysis.ats_score if latest_analysis else None

    return {
        "average_score": average_score,
        "total_interviews": len(evaluations),
        "weak_topics": weak_topics,
        "ats_score": ats_score,
        "recommendation": recommendation
    }
