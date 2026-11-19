from typing import List, Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field
from chat import tanya

app = FastAPI()

class Giliran(BaseModel):
    peran: Literal["user", "bot"]
    isi: str = Field(max_length=500)

class ChatRequest(BaseModel):
    pesan: str = Field(min_length=1, max_length=500)
    riwayat: List[Giliran] = Field(default_factory=list, max_length=6)

@app.post("/chat")
def chat(req: ChatRequest):
    riwayat = [g.model_dump() for g in req.riwayat]
    return {"jawaban": tanya(req.pesan, riwayat)}