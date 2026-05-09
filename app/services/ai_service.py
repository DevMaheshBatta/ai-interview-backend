
import os
from google import genai
from app.config import settings

# ✅ ONE client, defined at module level
client = genai.Client(api_key=settings.GEMINI_API_KEY)

MODEL = "gemini-2.0-flash"  # ✅ current model, replaces gemini-1.5-flash


def ask_resume_question(resume_text: str, question: str) -> str:
    prompt = f"""You are an AI interview coach.
Resume:
{resume_text}

Question: {question}
Answer as a helpful coach."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    return response.text


def evaluate_answer(question: str, user_answer: str) -> dict:
    prompt = f"""Evaluate this interview answer and respond ONLY in JSON:
{{
  "score": <int 1-10>,
  "technical_feedback": "<string>",
  "improvements": "<string>"
}}

Question: {question}
Answer: {user_answer}"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    import json
    text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def analyze_resume(resume_text: str) -> dict:
    prompt = f"""Analyze this resume and respond ONLY in JSON:
{{
  "ats_score": <int 1-100>,
  "strengths": ["...", "..."],
  "missing_skills": ["...", "..."],
  "improvements": ["...", "..."]
}}

Resume:
{resume_text}"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    import json
    text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def generate_weak_area_summary(weak_topics: list, average_score: float) -> str:
    prompt = f"""A candidate scored {average_score}/10 on average and struggled with: {weak_topics}.
Give 3 concise improvement recommendations."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    return response.text