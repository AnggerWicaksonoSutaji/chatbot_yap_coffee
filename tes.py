import ollama

r = ollama.chat(
    model="qwen2.5:1.5b",
    messages=[{"role": "user", "content": "Apa itu chatbot? Jawab singkat."}],
)
print(r["message"]["content"])

e = ollama.embeddings(model="nomic-embed-text", prompt="tes embedding")
print("Dimensi embedding:", len(e["embedding"]))