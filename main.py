from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI()

# URL de tu modelo local
URL_LLM = "http://127.0.0.1:1234/v1/chat/completions"

# Modelo de datos esperado por FastAPI
class ChatRequest(BaseModel):
    prompt: str
    max_tokens: int = 50

@app.post("/chat/")
def chat_with_llm(request: ChatRequest):
    payload = {
        "messages": [{"role": "user", "content": request.prompt}],
        "max_tokens": request.max_tokens
    }

    try:
        response = requests.post(URL_LLM, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error al conectar con el LLM: {str(e)}")
