from google import genai
from app.config import settings
import json

client = genai.Client(api_key=settings.GEMINI_API_KEY)

MODEL_NAME = "models/gemini-2.5-flash"

def ask_resume_question(resume_text: str, question: str):

    prompt = f"""
    You are an AI Interview Copilot.

    Candidate Resume:
    {resume_text}

    Interview Question:
    {question}

    Provide a professional, structured interview answer based on the resume.
    """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


def evaluate_answer(question: str, user_answer: str):

    prompt = f"""
    You are a strict senior technical interviewer.

    Evaluate the candidate answer.

    Question:
    {question}

    Candidate Answer:
    {user_answer}

    IMPORTANT:
    Return ONLY valid JSON.
    No explanation.
    No markdown.
    No text outside JSON.

    Format:
    {{
        "score": 1-10,
        "technical_feedback": "detailed feedback",
        "improvements": "specific improvements"
    }}
    """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    raw_text = response.text.strip()

    try:
        # Try direct JSON parse
        return json.loads(raw_text)

    except json.JSONDecodeError:
        # Extract JSON block using regex (fallback)
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError(f"Model returned invalid JSON:\n{raw_text}")
        

def generate_weak_area_summary(weak_topics, average_score):

    prompt = f"""
    You are a senior technical mentor.

    The candidate has an average interview score of {average_score}.

    Weak topics:
    {weak_topics}

    Provide a short professional improvement recommendation.
    Keep it concise (4-5 lines).
    """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text.strip()
def analyze_resume(resume_text: str):

    prompt = f"""
    You are an ATS (Applicant Tracking System).

    Analyze the resume below and return ONLY valid JSON.

    Resume:
    {resume_text}

    Return format:

    {{
        "ats_score": 0-100,
        "strengths": ["point1", "point2"],
        "missing_skills": ["skill1", "skill2"],
        "improvements": ["improvement1", "improvement2"]
    }}

    No extra text. Only JSON.
    """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    import json, re

    raw_text = response.text.strip()

    try:
        return json.loads(raw_text)
    except:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError("Invalid JSON from ATS model")
