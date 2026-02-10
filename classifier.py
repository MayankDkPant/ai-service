import requests
import json
import re
from validator import ClassificationResponse

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3:8b"

SYSTEM_PROMPT = """
You are a civic complaint classification engine.

Respond ONLY in strict JSON format:

{
  "intent": "COMPLAINT",
  "department": "SANITATION | WATER | ELECTRICITY | ROADS | PUBLIC_SAFETY | OTHER",
  "priority": "LOW | MEDIUM | HIGH",
  "confidence": 0.0-1.0
}

Rules:
- Choose exactly ONE department.
- Do NOT combine values.
- No explanation text.
- No markdown.
- No extra fields.
- If unsure, choose OTHER.
"""

# ----------------------------
# INPUT SANITIZATION
# ----------------------------
def sanitize_input(text: str) -> str:
    return text.strip()[:1000]


# ----------------------------
# CALL OLLAMA
# ----------------------------
def call_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "top_p": 0.1,
            "num_predict": 200
        }
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=10)
    response.raise_for_status()

    return response.json()["response"]


# ----------------------------
# EXTRACT JSON FROM LLM OUTPUT
# ----------------------------
def extract_json(text: str) -> dict:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in response")

    return json.loads(match.group())


# ----------------------------
# DEPARTMENT OVERRIDE RULES
# ----------------------------
def override_department(text: str, predicted: str) -> str:
    lower = text.lower()

    if any(word in lower for word in [
        "street light", "streetlight", "power line",
        "electricity", "transformer", "electric pole"
    ]):
        return "ELECTRICITY"

    if any(word in lower for word in [
        "garbage", "waste", "drain", "sewage",
        "overflow", "trash"
    ]):
        return "SANITATION"

    if any(word in lower for word in [
        "water supply", "pipeline", "tap water",
        "water leakage", "no water"
    ]):
        return "WATER"

    if any(word in lower for word in [
        "road damage", "pothole", "road crack"
    ]):
        return "ROADS"

    if any(word in lower for word in [
        "fight", "harassment", "theft",
        "unsafe", "crime"
    ]):
        return "PUBLIC_SAFETY"

    return predicted


# ----------------------------
# PRIORITY OVERRIDE RULES
# ----------------------------
def override_priority(text: str, predicted: str) -> str:
    lower = text.lower()

    # Safety escalation
    if any(word in lower for word in [
        "electric shock", "live wire", "fire",
        "accident", "collapse"
    ]):
        return "HIGH"

    # Duration-based escalation using regex
    import re
    match = re.search(r'(\d+)\s*day', lower)
    if match:
        days = int(match.group(1))
        if days >= 4:
            return "HIGH"

    return predicted



# ----------------------------
# APPLY ALL OVERRIDES
# ----------------------------
def apply_overrides(text: str, validated: ClassificationResponse) -> ClassificationResponse:
    original_department = validated.department
    original_priority = validated.priority

    # Department override
    validated.department = override_department(
        text,
        validated.department
    )

    # Priority override
    validated.priority = override_priority(
        text,
        validated.priority
    )

    # Log changes (for debugging / analytics)
    if original_department != validated.department:
        print(f"[Override] Department changed: {original_department} → {validated.department}")

    if original_priority != validated.priority:
        print(f"[Override] Priority changed: {original_priority} → {validated.priority}")

    return validated


# ----------------------------
# MAIN CLASSIFICATION FUNCTION
# ----------------------------
def classify(text: str) -> dict:
    try:
        clean_text = sanitize_input(text)

        full_prompt = SYSTEM_PROMPT + f"\nComplaint: {clean_text}"

        # 1️⃣ AI Suggestion
        raw_output = call_ollama(full_prompt)

        # 2️⃣ Extract JSON
        json_data = extract_json(raw_output)

        # 3️⃣ Validate structure
        validated = ClassificationResponse(**json_data)

        # 4️⃣ Confidence enforcement
        if validated.confidence < 0.6:
            validated.department = "OTHER"

        # 5️⃣ Deterministic override layer
        validated = apply_overrides(clean_text, validated)

        return validated.model_dump()

    except Exception as e:
        print(f"[Classifier Error] {str(e)}")

        # Safe fallback
        return {
            "intent": "COMPLAINT",
            "department": "OTHER",
            "priority": "MEDIUM",
            "confidence": 0.5
        }
