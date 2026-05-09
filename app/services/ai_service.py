import json
from groq import Groq
from app.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"  # fast, free, capable


def _chat(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content


def ask_resume_question(resume_text: str, question: str) -> str:
    prompt = f"""You are an AI interview coach.
Resume:
{resume_text}

Question: {question}
Give a helpful, concise answer."""
    return _chat(prompt)


def evaluate_answer(question: str, user_answer: str) -> dict:
    prompt = f"""Evaluate this interview answer. Respond ONLY in raw JSON, no markdown or backticks:
{{"score": <int 1-10>, "technical_feedback": "<string>", "improvements": "<string>"}}

Question: {question}
Answer: {user_answer}"""
    text = _chat(prompt).strip().replace("```json", "").replace("```", "")
    return json.loads(text)


def analyze_resume(resume_text: str) -> dict:
    prompt = f"""Analyze this resume. Respond ONLY in raw JSON, no markdown or backticks:
{{"ats_score": <int 1-100>, "strengths": ["...", "..."], "missing_skills": ["...", "..."], "improvements": ["...", "..."]}}

Resume:
{resume_text}"""
    text = _chat(prompt).strip().replace("```json", "").replace("```", "")
    return json.loads(text)


def generate_weak_area_summary(weak_topics: list, average_score: float) -> str:
    prompt = f"""A candidate scored {average_score}/10 on average and struggled with: {weak_topics}.
Give 3 concise, actionable improvement recommendations."""
    return _chat(prompt)