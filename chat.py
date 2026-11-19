import re
import chromadb, ollama

CHAT_MODEL = "qwen2.5:1.5b"
EMBED_MODEL = "nomic-embed-text"
MAX_JARAK = 0.6
TOP_K = 3

col = chromadb.PersistentClient(path="./db").get_collection("website")

with open("knowledge/menu.md", encoding="utf-8") as f:
    MENU = f.read()

SYSTEM = """Kamu adalah asisten aplikasi Yap Coffee (pre-order kopi).
Aturan:
1. Jawab dalam bahasa Indonesia, singkat dan ramah.
2. Gunakan HANYA informasi di KONTEKS. Jangan menambah fakta dari pengetahuanmu sendiri.
3. Pertanyaan tentang memesan, menu, harga, pembayaran, pengambilan, atau fitur aplikasi SELALU berkaitan dengan Yap Coffee.
4. Hanya jika pertanyaan jelas tentang hal lain (politik, berita, pengetahuan umum, pemrograman), balas persis: TIDAK_RELEVAN
5. Jika berkaitan dengan Yap Coffee tetapi jawabannya tidak ada di KONTEKS, balas persis: TIDAK_TAHU
6. Untuk sapaan biasa (halo, apa kabar), balas singkat lalu tanyakan apa yang bisa dibantu."""

TOLAK = ("Maaf, saya tidak punya informasi tentang itu. "
         'Silakan tekan tombol "Hubungi Penjual" untuk bertanya langsung.')

TOLAK_LUAR = "Maaf, saya hanya bisa membantu pertanyaan seputar aplikasi Yap Coffee."

CEK = """Tugasmu menentukan apakah sebuah pesan boleh dijawab oleh asisten aplikasi pre-order kopi "Yap Coffee".
Jawab hanya satu kata: YA atau TIDAK.
YA jika pesan berisi sapaan, basa-basi singkat, atau pertanyaan tentang menu, harga, cara pesan, pembayaran, pengambilan, akun, fitur aplikasi, atau penjual.
TIDAK jika pesan tentang hal lain (politik, tokoh, berita, sejarah, matematika, pemrograman, dan sebagainya).

Contoh:
Pesan: halo ->YA
Pesan: apa kabar ->YA
Pesan: berapa harga cappuccino ->YA
Pesan: bagaimana cara pesan ->YA
Pesan: apakah saya bisa memesan es kopi susu ->YA
Pesan: siapa presiden indonesia ->TIDAK
Pesan: ibukota perancis apa ->TIDAK
Pesan: buatkan kode python ->TIDAK"""

CUE_LANJUTAN = re.compile(
    r"\b(tadi|itu|tersebut|yang|kalau|kalo|harganya|rasanya|lainnya|juga|terus|lalu|nya)\b",
    re.I,
)

POLA_DAFTAR_MENU = re.compile(
    r"(menu apa( saja| aja)?|daftar menu|ada menu apa|apa saja menunya|menu apa yang ada)",
    re.I,
)

def daftar_menu():
    """Bangun daftar menu dari tabel di menu.md (hanya tabel di bawah heading berisi 'menu')."""
    baris, heading = [], ""
    for b in MENU.splitlines():
        if b.startswith("#"):
            heading = b.lower()
            continue
        if "menu" not in heading or not b.startswith("|") or "---" in b:
            continue
        sel = [s.strip() for s in b.strip("|").split("|")]
        if len(sel) < 2 or sel[0].lower() == "menu":
            continue
        harga = next((s for s in sel[1:] if "Rp" in s), "")
        baris.append(f"- {sel[0]}" + (f": {harga}" if harga else ""))
    unik = list(dict.fromkeys(baris))
    if not unik:
        return TOLAK
    return ("Menu yang tersedia saat ini:\n" + "\n".join(unik) +
            "\n\nDaftar terbaru bisa dilihat di halaman Menu aplikasi.")

def pesan_sebelumnya(riwayat):
    """Ambil pesan pengguna terakhir dari riwayat."""
    return next((g["isi"] for g in reversed(riwayat) if g["peran"] == "user"), "")

def relevan(pertanyaan, riwayat):
    sebelumnya = pesan_sebelumnya(riwayat)

    if sebelumnya and len(pertanyaan.split()) <= 8 and CUE_LANJUTAN.search(pertanyaan):
        bot_terakhir = next((g["isi"] for g in reversed(riwayat) if g["peran"] == "bot"), "")
        if bot_terakhir != TOLAK_LUAR:
            return True

    r = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": CEK},
            {"role": "user", "content": f"Pesan: {pertanyaan} ->"},
        ],
        options={"temperature": 0, "num_predict": 3, "num_ctx": 2048},
    )
    return r["message"]["content"].strip().upper().startswith("YA")

def bersihkan(q):
    """Buang sapaan di awal agar pencarian fokus ke isi pertanyaan."""
    q = re.sub(r"^\s*(halo+|hai+|hi|selamat (pagi|siang|sore|malam))\W*", "", q, flags=re.I)
    return q.strip() or q

def tanya(pertanyaan, riwayat=None, debug=False):
    riwayat = riwayat or []

    # pertanyaan daftar menu dijawab langsung dari data, tanpa model
    if POLA_DAFTAR_MENU.search(pertanyaan):
        return daftar_menu()

    if not relevan(pertanyaan, riwayat):
        return TOLAK_LUAR

    kueri = bersihkan(pertanyaan)
    sebelumnya = pesan_sebelumnya(riwayat)
    if sebelumnya and len(pertanyaan.split()) <= 6:
        kueri = sebelumnya + " " + kueri

    emb = ollama.embeddings(model=EMBED_MODEL, prompt="search_query: " + kueri)["embedding"]
    hasil = col.query(query_embeddings=[emb], n_results=TOP_K)

    cocok = []
    for doc, jarak in zip(hasil["documents"][0], hasil["distances"][0]):
        if debug:
            print(f"  [jarak={jarak:.3f}] {doc[:60]!r}")
        if jarak <= MAX_JARAK:
            cocok.append(doc)

    konteks = "MENU:\n" + MENU + "\n---\n" + "\n---\n".join(cocok)

    pesan = [{"role": "system", "content": SYSTEM}]
    for g in riwayat[-4:]:
        pesan.append({"role": "user" if g["peran"] == "user" else "assistant", "content": g["isi"]})
    pesan.append({"role": "user", "content": f"KONTEKS:\n{konteks}\n\nPERTANYAAN: {pertanyaan}"})

    r = ollama.chat(
        model=CHAT_MODEL,
        messages=pesan,
        options={"temperature": 0, "num_ctx": 4096},
    )
    jawab = r["message"]["content"].strip()
    if jawab.startswith("TIDAK_RELEVAN"):
        return TOLAK_LUAR
    if jawab.startswith("TIDAK_TAHU"):
        return TOLAK
    return jawab

if __name__ == "__main__":
    print("Ketik pertanyaan (Ctrl+C untuk keluar)")
    riwayat = []
    while True:
        try:
            q = input("\nAnda: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not q:
            continue
        jawab = tanya(q, riwayat, debug=True)
        print("Bot :", jawab)
        riwayat += [{"peran": "user", "isi": q}, {"peran": "bot", "isi": jawab}]
        riwayat = riwayat[-6:]