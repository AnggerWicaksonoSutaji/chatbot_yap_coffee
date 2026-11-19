import sys
import chromadb, ollama

col = chromadb.PersistentClient(path="./db").get_collection("website")
q = " ".join(sys.argv[1:]) or "cara daftar akun"

emb = ollama.embeddings(model="nomic-embed-text", prompt="search_query: " + q)["embedding"]
hasil = col.query(query_embeddings=[emb], n_results=3)

for doc, meta, jarak in zip(hasil["documents"][0], hasil["metadatas"][0], hasil["distances"][0]):
    print(f"[{meta['sumber']}] jarak={jarak:.3f}\n{doc}\n{'-'*40}")
    