import os, glob
import chromadb, ollama

EMBED_MODEL = "nomic-embed-text"
MAX_CHARS = 800
OVERLAP = 100

def embed_dokumen(teks):
    return ollama.embeddings(model=EMBED_MODEL, prompt="search_document: " + teks)["embedding"]

def ekor(teks):
    """Ambil ±OVERLAP karakter terakhir, mulai dari batas kata."""
    t = teks[-OVERLAP:]
    i = t.find(" ")
    return t[i + 1:] if i != -1 else t

def pecah(teks):
    """Pecah per paragraf, gabungkan sampai ~MAX_CHARS, dengan sedikit overlap."""
    paragraf = [p.strip() for p in teks.split("\n\n") if p.strip()]
    chunks, buf = [], ""
    for p in paragraf:
        if len(buf) + len(p) + 2 <= MAX_CHARS:
            buf = f"{buf}\n\n{p}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = (ekor(buf) + "\n\n" + p).strip() if buf else p
    if buf:
        chunks.append(buf)
    return chunks

client = chromadb.PersistentClient(path="./db")
try:
    client.delete_collection("website")   # indeks ulang dari nol
except Exception:
    pass
col = client.create_collection("website", metadata={"hnsw:space": "cosine"})

total = 0
for path in sorted(glob.glob("knowledge/*.md") + glob.glob("knowledge/*.txt")):
    with open(path, encoding="utf-8") as f:
        isi = f.read()
    for i, c in enumerate(pecah(isi)):
        col.add(
            ids=[f"{os.path.basename(path)}-{i}"],
            documents=[c],
            embeddings=[embed_dokumen(c)],
            metadatas=[{"sumber": os.path.basename(path)}],
        )
        total += 1
    print(f"OK  {path}")

print(f"Selesai: {total} potongan teks diindeks.")