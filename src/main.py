# ai-generated: 100% - szkielet wygenerowany przez asystenta AI
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "svcdesk"}