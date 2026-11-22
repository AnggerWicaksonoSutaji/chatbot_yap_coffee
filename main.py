from typing import List, Literal, Optional
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
    menu: List[dict] = Field(default_factory=list, max_length=100)
    opsi: Optional[dict] = None
    jadwal: Optional[List[dict]] = Field(default=None, max_length=10)
    biaya: Optional[dict] = None
    pesanan: Optional[List[dict]] = Field(default=None, max_length=5)
    pesanan_lama: Optional[List[dict]] = Field(default=None, max_length=5)

@app.post("/chat")
def chat(req: ChatRequest):
    riwayat = [g.model_dump() for g in req.riwayat]
    return {"jawaban": tanya(
        req.pesan, riwayat,
        menu=req.menu, opsi=req.opsi, pesanan=req.pesanan,
        jadwal=req.jadwal, biaya=req.biaya, pesanan_lama=req.pesanan_lama,
    )}