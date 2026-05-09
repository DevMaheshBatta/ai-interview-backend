import google.generativeai as genai
from app.config import settings

# ✅ configure once at module level
genai.configure(api_key=settings.GEMINI_API_KEY)

# ✅ use a model that actually exists
MODEL_NAME = "gemini-2.0-flash"  # or "gemini-2.0-flash"


def ask_resume_question(resume_text: str, question: str) -> str:
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"You are an AI interview coach.\nResume:\n{resume_text}\n\nQuestion: {question}"
    response = model.generate_content(prompt)
    return response.text


def evaluate_answer(question: str, user_answer: str) -> dict:
    import json
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""Evaluate this interview answer. Respond ONLY in JSON, no markdown:
{{"score": <int 1-10>, "technical_feedback": "<str>", "improvements": "<str>"}}

Question: {question}
Answer: {user_answer}"""
    response = model.generate_content(prompt)
    text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def analyze_resume(resume_text: str) -> dict:
    import json
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""Analyze this resume. Respond ONLY in JSON, no markdown:
{{"ats_score": <int 1-100>, "strengths": ["..."], "missing_skills": ["..."], "improvements": ["..."]}}

Resume:
{resume_text}"""
    response = model.generate_content(prompt)
    text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def generate_weak_area_summary(weak_topics: list, average_score: float) -> str:
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"Candidate scored {average_score}/10 and struggled with: {weak_topics}. Give 3 concise improvement tips."
    response = model.generate_content(prompt)
    return response.text