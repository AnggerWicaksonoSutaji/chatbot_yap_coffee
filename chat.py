import re
import chromadb, ollama

CHAT_MODEL = "qwen2.5:1.5b"
EMBED_MODEL = "nomic-embed-text"
MAX_JARAK = 0.6
TOP_K = 3
PAKAI_FILTER = True      # matikan setelah memakai model hasil fine-tuning

col = chromadb.PersistentClient(path="./db").get_collection("website")

SYSTEM = """Kamu adalah asisten aplikasi Yap Coffee (pre-order kopi).
Aturan:
1. Jawab dalam bahasa Indonesia, singkat dan ramah.
2. Gunakan HANYA informasi di KONTEKS. Jangan menambah fakta dari pengetahuanmu sendiri.
3. Pertanyaan tentang memesan, menu, harga, pembayaran, pengambilan, pesanan, atau fitur aplikasi SELALU berkaitan dengan Yap Coffee.
4. Hanya jika pertanyaan jelas tentang hal lain (politik, berita, pengetahuan umum, pemrograman), balas persis: TIDAK_RELEVAN
5. Jika berkaitan dengan Yap Coffee tetapi jawabannya tidak ada di KONTEKS, balas persis: TIDAK_TAHU
6. Untuk sapaan biasa (halo, apa kabar), balas singkat lalu tanyakan apa yang bisa dibantu.
7. Pertanyaan tentang pesanan pengguna dijawab HANYA dari blok PESANAN PENGGUNA. Jika blok itu tidak ada, katakan kamu tidak bisa melihat pesanan dan arahkan ke tab Orders. Jika isinya tidak ada pesanan aktif, sampaikan itu.
8. Pertanyaan tentang jadwal atau lokasi pengambilan dijawab dari blok JADWAL PENGAMBILAN, tentang biaya dari blok BIAYA, dan tentang pesanan lama dari blok RIWAYAT PESANAN PENGGUNA. Jangan menyebut blok yang tidak ada di KONTEKS."""

TOLAK = ("Maaf, saya tidak punya informasi tentang itu. "
         'Silakan tekan tombol "Hubungi Penjual" untuk bertanya langsung.')

TOLAK_LUAR = "Maaf, saya hanya bisa membantu pertanyaan seputar aplikasi Yap Coffee."

MENU_GAGAL = ("Maaf, daftar menu belum bisa saya baca saat ini. "
              "Silakan lihat langsung di halaman Menu aplikasi.")

CEK = """Tugasmu menentukan apakah sebuah pesan boleh dijawab oleh asisten aplikasi pre-order kopi "Yap Coffee".
Jawab hanya satu kata: YA atau TIDAK.
YA jika pesan berisi sapaan, basa-basi singkat, atau pertanyaan tentang menu, harga, cara pesan, pembayaran, pengambilan, pesanan, akun, fitur aplikasi, atau penjual.
TIDAK jika pesan tentang hal lain (politik, tokoh, berita, sejarah, matematika, pemrograman, dan sebagainya).

Contoh:
Pesan: halo ->YA
Pesan: apa kabar ->YA
Pesan: berapa harga cappuccino ->YA
Pesan: bagaimana cara pesan ->YA
Pesan: apakah saya bisa memesan es kopi susu ->YA
Pesan: pesanan saya sudah siap belum ->YA
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

# Pertanyaan yang jawabannya hanya ada di data menu/opsi dari backend.
POLA_SOAL_MENU = re.compile(r"harga|ukuran|large|reguler|manis|sugar|kopi|minuman|makanan", re.I)

# Kata yang pasti berkaitan dengan aplikasi: lolos tanpa bertanya ke model.
KATA_YAP = re.compile(
    r"\b(menu|kopi|coffee|latte|espresso|americano|cappuccino|matcha|minuman|makanan|"
    r"pesan|memesan|pesanan|order|harga|bayar|pembayaran|qris|ambil|pengambilan|kloter|"
    r"checkout|keranjang|login|akun|profil|penjual|yap|aplikasi|ukuran|manis|"
    r"jadwal|lokasi|riwayat|pajak|biaya|stok|tambahan|batal|dibatalkan|selesai)\b",
    re.I,
)

# ---------- pertanyaan berdasarkan kategori ----------
POLA_NIAT_PILIH = re.compile(
    r"\b(pesan|memesan|mau|ingin|pengen|pengin|beli|membeli|ada|tersedia|menu|rekomendasi|"
    r"pilihan|lihat|tampilkan|tunjukkan|daftar|apa saja|apa aja)\b",
    re.I,
)
# Pertanyaan cara/harga/waktu bukan permintaan daftar: biarkan jalur biasa.
POLA_BUKAN_DAFTAR = re.compile(
    r"\b(cara|bagaimana|gimana|kenapa|mengapa|kapan|dimana|di mana|berapa|harga)\b", re.I
)
KATA_KOPI = {"kopi", "coffee"}
KATA_MINUMAN = {"minuman"}
KATA_MAKANAN = {"makanan", "camilan", "cemilan", "snack"}
ABAIKAN = {"semua", "menu", "based", "yang", "untuk", "dengan"}

# ---------- format data dari backend ----------
def bersih(s, n=80):
    """Satu baris, tanpa karakter tabel, dipotong, agar data tidak merusak prompt."""
    return re.sub(r"\s+", " ", str(s or "")).replace("|", "/").strip()[:n]

def angka(n):
    try:
        return int(float(n))
    except (TypeError, ValueError):
        return 0

def desimal(n):
    try:
        return f"{float(n):g}"
    except (TypeError, ValueError):
        return bersih(n, 10)

def rp(n):
    try:
        return "Rp " + f"{int(float(n)):,}".replace(",", ".")
    except (TypeError, ValueError):
        return bersih(n, 20)

def kata(teks):
    return re.findall(r"[a-z0-9]+", str(teks).lower())

def token_kategori(nama):
    """Kata khas sebuah kategori (tanpa kata umum seperti 'kopi' atau 'semua')."""
    return {t for t in kata(nama)
            if len(t) >= 4 and t not in ABAIKAN and t not in KATA_KOPI}

def teks_tambahan(m):
    out = []
    for t in (m.get("tambahan") or [])[:4]:
        if not isinstance(t, dict):
            continue
        label = bersih(t.get("label"), 30)
        if not label:
            continue
        biaya = angka(t.get("biaya"))
        out.append(label + (f" (+{rp(biaya)})" if biaya > 0 else ""))
    return "; ".join(out)

def teks_menu(menu):
    baris = ["| Menu | Kategori | Harga | Tambahan | Deskripsi |", "|---|---|---|---|---|"]
    ada = False
    for m in menu[:100]:
        if not isinstance(m, dict):
            continue
        nama = bersih(m.get("nama"))
        if not nama:
            continue
        if m.get("habis"):
            nama += " (stok habis)"
        baris.append(
            f"| {nama} | {bersih(m.get('kategori'), 30)} | {rp(m.get('harga'))} | "
            f"{teks_tambahan(m)} | {bersih(m.get('deskripsi'), 60)} |"
        )
        ada = True
    return "\n".join(baris) if ada else "(daftar menu tidak tersedia saat ini)"

def teks_opsi(opsi):
    if not isinstance(opsi, dict):
        return ""
    ukuran = []
    for u in (opsi.get("ukuran") or [])[:10]:
        if not isinstance(u, dict):
            continue
        label = bersih(u.get("label"), 30)
        if not label:
            continue
        detail = bersih(u.get("detail"), 30)
        tambah = angka(u.get("tambahan"))
        biaya = f"tambah {rp(tambah)}" if tambah > 0 else "tanpa biaya tambahan"
        ukuran.append(f"{label} ({detail + ', ' if detail else ''}{biaya})")
    manis = [bersih(x, 30) for x in (opsi.get("manis") or [])[:10] if bersih(x, 30)]
    out = []
    if ukuran:
        out.append("Ukuran gelas: " + "; ".join(ukuran))
    if manis:
        out.append("Tingkat manis: " + ", ".join(manis))
    return ("OPSI PESANAN:\n" + "\n".join(out)) if out else ""

def teks_jadwal(jadwal):
    kosong = "(tidak ada jadwal pengambilan yang bisa dipesan saat ini)"
    if not jadwal:
        return kosong
    out = []
    for j in jadwal[:6]:
        if not isinstance(j, dict):
            continue
        detail = bersih(j.get("detail_lokasi"), 60)
        out.append(
            f"- {bersih(j.get('nama'), 40)}: {bersih(j.get('tanggal'), 20)}, "
            f"pengambilan {bersih(j.get('mulai'), 8)}-{bersih(j.get('selesai'), 8)} WIB, "
            f"batas pemesanan {bersih(j.get('batas_pesan'), 8)} WIB, "
            f"lokasi {bersih(j.get('lokasi'), 60)}" + (f" ({detail})" if detail else "")
        )
    return "\n".join(out) or kosong

def teks_biaya(biaya):
    if not isinstance(biaya, dict):
        return ""
    out = []
    if biaya.get("pajak_persen") is not None:
        out.append(f"Pajak {desimal(biaya['pajak_persen'])}% dari subtotal.")
    if biaya.get("biaya_layanan") is not None:
        out.append(f"Biaya layanan {rp(biaya['biaya_layanan'])}.")
    if biaya.get("batas_bayar_menit") is not None:
        out.append(f"Batas waktu pembayaran {angka(biaya['batas_bayar_menit'])} menit setelah pesanan dikonfirmasi.")
    return "\n".join(out)

def teks_pesanan(pesanan, kosong="(tidak ada pesanan aktif)"):
    if not pesanan:
        return kosong
    out = []
    for p in pesanan[:5]:
        if not isinstance(p, dict):
            continue
        out.append(
            f"- Pesanan {bersih(p.get('nomor'), 20)}: status {bersih(p.get('status'), 60)}; "
            f"pengambilan {bersih(p.get('tanggal'), 20)} {bersih(p.get('kloter'), 40)} "
            f"di {bersih(p.get('lokasi'), 60)}; total {rp(p.get('total'))}"
        )
        isi = []
        for it in (p.get("item") or [])[:8]:
            if not isinstance(it, dict):
                continue
            rincian = ", ".join(x for x in (
                bersih(it.get("ukuran"), 20), bersih(it.get("manis"), 20), bersih(it.get("catatan"), 40)
            ) if x)
            isi.append(f"{angka(it.get('jumlah'))}x {bersih(it.get('nama'), 40)}"
                       + (f" ({rincian})" if rincian else ""))
        if isi:
            out.append("  Isi: " + "; ".join(isi))
    return "\n".join(out) or kosong

def daftar_menu(menu):
    baris = []
    for m in menu[:100]:
        if not isinstance(m, dict):
            continue
        nama = bersih(m.get("nama"))
        if not nama:
            continue
        habis = " (stok habis)" if m.get("habis") else ""
        baris.append(f"- {nama}: {rp(m.get('harga'))}{habis}")
    if not baris:
        return MENU_GAGAL
    return ("Menu yang tersedia saat ini:\n" + "\n".join(baris) +
            "\n\nDaftar terbaru bisa dilihat di halaman Menu aplikasi.")

# ---------- menu per kategori ----------
def pilih_menu_kategori(pertanyaan, menu):
    """
    Kalau pertanyaan menyebut kategori atau jenis menu ("mau pesan kopi", "ada makanan?"),
    kembalikan (judul, {kategori: [menu, ...]}). Selain itu None.
    """
    q = pertanyaan.lower()
    if not POLA_NIAT_PILIH.search(q) or POLA_BUKAN_DAFTAR.search(q):
        return None

    item = [m for m in menu if isinstance(m, dict) and bersih(m.get("nama"))]
    if not item:
        return None
    # Menyebut satu menu tertentu: biarkan jalur biasa yang menjawab.
    if any(bersih(m["nama"]).lower() in q for m in item):
        return None

    kt = set(kata(q))
    semua = {}
    for m in item:
        semua.setdefault(bersih(m.get("kategori"), 40) or "Lainnya", []).append(m)

    # 1) nama kategori disebut lengkap, 2) salah satu kata khas kategori disebut
    cocok = [k for k in semua if re.search(rf"\b{re.escape(k.lower())}\b", q)]
    if not cocok:
        cocok = [k for k in semua if token_kategori(k) & kt]
    if cocok:
        judul = "kategori " + ", ".join(cocok)
        return judul, {k: semua[k] for k in cocok}

    # 3) kata umum: makanan / minuman / kopi
    def saring(fungsi):
        g = {}
        for k, daftar in semua.items():
            ok = [m for m in daftar if fungsi(k, m)]
            if ok:
                g[k] = ok
        return g

    if kt & KATA_MAKANAN:
        judul, grup = "makanan", saring(lambda k, m: m.get("jenis") == "makanan")
    elif kt & KATA_MINUMAN:
        judul, grup = "minuman", saring(lambda k, m: m.get("jenis") != "makanan")
    elif kt & KATA_KOPI:
        judul, grup = "kopi", saring(
            lambda k, m: m.get("jenis") != "makanan" and "non" not in kata(k)
        )
    else:
        return None
    return (judul, grup) if grup else None

def jawab_kategori(pertanyaan, menu):
    hasil = pilih_menu_kategori(pertanyaan, menu)
    if not hasil:
        return None
    judul, grup = hasil

    def baris_menu(m):
        habis = " (stok habis)" if m.get("habis") else ""
        return f"- {bersih(m.get('nama'))}: {rp(m.get('harga'))}{habis}"

    out = [f"Berikut menu {judul} yang tersedia:"]
    if len(grup) == 1:
        out += [baris_menu(m) for m in next(iter(grup.values()))]
    else:
        for k, daftar in grup.items():
            out.append(f"\n{k}")
            out += [baris_menu(m) for m in daftar]
    out.append('\nUntuk memesan, buka halaman Menu lalu tekan tombol "+" pada menu pilihan.')
    return "\n".join(out)

# ---------- logika chat ----------
def pesan_sebelumnya(riwayat):
    return next((g["isi"] for g in reversed(riwayat) if g["peran"] == "user"), "")

def relevan(pertanyaan, riwayat):
    # Kata kunci aplikasi: tidak perlu bertanya ke model (yang kadang salah menolak).
    if KATA_YAP.search(pertanyaan):
        return True
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
    q = re.sub(r"^\s*(halo+|hai+|hi|selamat (pagi|siang|sore|malam))\W*", "", q, flags=re.I)
    return q.strip() or q

def tanya(pertanyaan, riwayat=None, menu=None, opsi=None, pesanan=None,
          jadwal=None, biaya=None, pesanan_lama=None, debug=False):
    riwayat = riwayat or []
    menu = menu or []

    if POLA_DAFTAR_MENU.search(pertanyaan):
        return daftar_menu(menu)

    # "mau pesan kopi", "ada makanan?", "es kopi susu apa saja?" -> daftar per kategori
    per_kategori = jawab_kategori(pertanyaan, menu)
    if per_kategori:
        return per_kategori

    # Tanpa data menu dari backend, jangan menebak harga, ukuran, atau isi menu.
    if not menu and POLA_SOAL_MENU.search(pertanyaan):
        return MENU_GAGAL

    if PAKAI_FILTER and not relevan(pertanyaan, riwayat):
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

    konteks = "MENU:\n" + teks_menu(menu)
    blok_opsi = teks_opsi(opsi)
    if blok_opsi:
        konteks += "\n---\n" + blok_opsi
    if jadwal is not None:
        konteks += "\n---\nJADWAL PENGAMBILAN YANG BISA DIPESAN:\n" + teks_jadwal(jadwal)
    blok_biaya = teks_biaya(biaya)
    if blok_biaya:
        konteks += "\n---\nBIAYA:\n" + blok_biaya
    if pesanan is not None:
        konteks += "\n---\nPESANAN PENGGUNA:\n" + teks_pesanan(pesanan)
    if pesanan_lama is not None:
        konteks += "\n---\nRIWAYAT PESANAN PENGGUNA:\n" + teks_pesanan(
            pesanan_lama, kosong="(tidak ada riwayat pesanan)")
    if cocok:
        konteks += "\n---\n" + "\n---\n".join(cocok)

    pesan = [{"role": "system", "content": SYSTEM}]
    for g in riwayat[-4:]:
        pesan.append({"role": "user" if g["peran"] == "user" else "assistant", "content": g["isi"]})
    pesan.append({"role": "user", "content": f"KONTEKS:\n{konteks}\n\nPERTANYAAN: {pertanyaan}"})

    r = ollama.chat(model=CHAT_MODEL, messages=pesan,
                    options={"temperature": 0, "num_ctx": 4096})
    jawab = r["message"]["content"].strip()
    if jawab.startswith("TIDAK_RELEVAN"):
        return TOLAK_LUAR
    if jawab.startswith("TIDAK_TAHU"):
        return TOLAK
    return jawab

if __name__ == "__main__":
    # HANYA untuk uji lewat terminal. API (main.py) selalu memakai data dari backend.
    MENU_UJI = [
        {"nama": "Kopi Uji A", "kategori": "Kopi Susu", "jenis": "minuman", "harga": 20000, "habis": False,
         "deskripsi": "menu uji", "tambahan": [{"label": "Extra Shot", "biaya": 5000}]},
        {"nama": "Kopi Uji B", "kategori": "Manual Brew", "jenis": "minuman", "harga": 27000, "habis": False,
         "deskripsi": "menu uji", "tambahan": []},
        {"nama": "Teh Uji", "kategori": "Non-Coffee", "jenis": "minuman", "harga": 15000, "habis": False,
         "deskripsi": "menu uji", "tambahan": []},
        {"nama": "Roti Uji", "kategori": "Makanan Ringan", "jenis": "makanan", "harga": 18000, "habis": False,
         "deskripsi": "menu uji", "tambahan": []},
    ]
    OPSI_UJI = {
        "ukuran": [{"label": "Reguler", "detail": "16 oz", "tambahan": 0},
                   {"label": "Large", "detail": "22 oz", "tambahan": 5000}],
        "manis": ["Normal", "Less Sugar", "No Sugar"],
    }
    JADWAL_UJI = [{"nama": "Kloter Uji", "tanggal": "2026-12-01", "mulai": "08:30", "selesai": "11:30",
                   "batas_pesan": "07:00", "lokasi": "Lokasi Uji", "detail_lokasi": ""}]
    BIAYA_UJI = {"pajak_persen": 11, "biaya_layanan": 2000, "batas_bayar_menit": 10}
    PESANAN_UJI = [{"nomor": "WK-0000", "status": "Siap Diambil", "tanggal": "2026-12-01",
                    "kloter": "Kloter Uji 08:30-11:30", "lokasi": "Lokasi Uji", "total": 50000,
                    "item": [{"nama": "Kopi Uji A", "jumlah": 2, "ukuran": "Large",
                              "manis": "Less Sugar", "catatan": ""}]}]
    print("Mode uji terminal (data uji, bukan data asli). Ctrl+C untuk keluar.")
    riwayat = []
    while True:
        try:
            q = input("\nAnda: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not q:
            continue
        jawab = tanya(q, riwayat, menu=MENU_UJI, opsi=OPSI_UJI, pesanan=PESANAN_UJI,
                      jadwal=JADWAL_UJI, biaya=BIAYA_UJI, debug=True)
        print("Bot :", jawab)
        riwayat += [{"peran": "user", "isi": q}, {"peran": "bot", "isi": jawab}]
        riwayat = riwayat[-6:]