from fastapi import FastAPI
from pydantic import BaseModel
from classifier import classify

app = FastAPI(title="CIRM AI Classification Service")


class ComplaintRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/classify")
def classify_complaint(request: ComplaintRequest):
    result= classify(request.text)
    print(f"Classification result: {result}")
    return result