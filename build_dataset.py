import glob, json, os, random, re
from chat import SYSTEM, MENU   # prompt dan menu sama dengan chatbot

random.seed(42)

# ---------- baca knowledge (kecuali menu.md) per bagian "## ..." ----------
def baca_bagian():
    out = {}
    def tambah(nama, kepala, buf):
        teks = "\n".join(buf).strip()
        if teks:
            out[(nama, kepala)] = teks
    for p in sorted(glob.glob("knowledge/*.md")):
        nama = os.path.basename(p)
        if nama == "menu.md":
            continue
        kepala, buf = "(awal)", []
        with open(p, encoding="utf-8") as f:
            for baris in f.read().splitlines():
                if baris.startswith("## "):
                    tambah(nama, kepala, buf)
                    kepala, buf = baris[3:].strip(), [baris]
                else:
                    buf.append(baris)
        tambah(nama, kepala, buf)
    return out

BAGIAN = baca_bagian()
NOISE = [k for k, v in BAGIAN.items() if "Rp" not in v and len(v) > 60]

def susun(menu_teks, wajib, n_noise):
    bag = [BAGIAN[k] for k in wajib]
    pool = [k for k in NOISE if k not in wajib]
    bag += [BAGIAN[k] for k in random.sample(pool, min(n_noise, len(pool)))]
    random.shuffle(bag)
    return "MENU:\n" + menu_teks + ("\n---\n" + "\n---\n".join(bag) if bag else "")

def ex(k, tanya, jawab):
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"KONTEKS:\n{k}\n\nPERTANYAAN: {tanya}"},
        {"role": "assistant", "content": jawab},
    ]}

PREFIX = ["", "", "", "halo, ", "kak, ", "permisi, ", "mau tanya, "]
def aug(q):
    return random.choice(PREFIX) + q

# ---------- fakta aplikasi & bisnis ----------
FAKTA = []
def f(src, qs, a, hanya_konteks=False):
    FAKTA.append(dict(src=src, qs=qs, a=a, hanya_konteks=hanya_konteks))

F, A, T, B = "faq.md", "alur-pemesanan.md", "fitur.md", "tentang.md"
N = "bisnis-akun.md"

f([(F, "Apa itu Yap Coffee?"), (B, "Apa itu Yap Coffee?")],
  ["apa itu yap coffee?", "yap coffee itu apa sih", "jelaskan tentang yap coffee",
   "aplikasi ini untuk apa?", "yap coffee ini apa?"],
  "Yap Coffee adalah aplikasi pre-order kopi. Anda memesan lewat aplikasi, lalu mengambil pesanan di titik pengambilan pada tanggal dan jam yang Anda pilih.")

f([(N, "Siapa pemilik Yap Coffee?")],
  ["siapa pemilik yap coffee?", "yap coffee punya siapa?", "siapa yang punya usaha ini?", "siapa pemiliknya?"],
  "Yap Coffee dimiliki oleh Yafi.")

f([(N, "Apakah bisa membeli langsung tanpa pre-order?")],
  ["bisa beli langsung di tempat?", "apakah bisa pesan tanpa pre-order?",
   "boleh datang langsung lalu beli?", "apakah menerima pembelian langsung?"],
  "Tidak. Yap Coffee hanya menerima pre-order, dan aplikasi ini adalah tempat memesannya.")

f([(N, "Apakah ada pengantaran?"), (F, "Apakah Yap Coffee melayani pengantaran?")],
  ["apakah bisa diantar?", "ada delivery nggak?", "bisa diantar ke rumah saya?", "apakah ada pengantaran?"],
  "Tidak ada pengantaran. Pesanan diambil sendiri, jadi Anda perlu datang ke lokasi pengambilan yang sudah ditentukan.")

f([(N, "Apakah ada promo atau voucher?")],
  ["ada promo?", "apakah ada voucher?", "ada diskon nggak?", "ada kode promo?"],
  "Saat ini tidak ada promo atau voucher.")

f([(A, "Langkah memesan"), (F, "Bagaimana cara memesan?")],
  ["bagaimana cara memesan?", "cara pesan gimana?", "gimana cara order kopi di sini?",
   "tolong jelaskan langkah pemesanan", "saya mau pesan, caranya bagaimana?"],
  'Buka Menu, tekan "+" pada menu pilihan, atur jumlah, ukuran, dan tingkat manis, lalu "Masukan Keranjang". Lanjut ke Checkout, pilih lokasi, tanggal, dan jam pengambilan, tekan "Konfirmasi Pre Order", lalu bayar lewat QRIS.')

f([(A, "Pembayaran"), (F, "Bagaimana cara membayar?")],
  ["bagaimana cara membayar?", "bayarnya pakai apa?", "metode pembayarannya apa?", "pembayaran lewat apa?"],
  'Pembayaran memakai QRIS. QRIS tampil setelah Anda menekan "Konfirmasi Pre Order".')

f([(N, "Berapa lama batas waktu pembayaran?")],
  ["berapa lama batas pembayaran?", "kapan batas waktu bayar?", "berapa menit saya harus membayar?",
   "ada batas waktu untuk membayar?"],
  "Batas waktu pembayaran adalah 10 menit.")

f([(F, 'Apa arti status "Belum Dibayar"?')],
  ['apa arti status belum dibayar?', 'status belum dibayar itu apa?', 'kenapa pesanan saya belum dibayar?', 'belum dibayar artinya apa?'],
  "Pesanan sudah dibuat tetapi belum dibayar. Selesaikan pembayaran agar pesanan diproses.")

f([(F, 'Apa arti status "Belum Diambil"?')],
  ['apa arti status belum diambil?', 'status belum diambil itu apa?', 'belum diambil artinya apa?', 'pesanan saya berstatus belum diambil'],
  "Pesanan sudah dibayar dan menunggu Anda ambil pada tanggal dan kloter yang dipilih.")

f([(F, 'Apa arti status "Siap Diambil"?')],
  ['apa arti status siap diambil?', 'status siap diambil itu apa?', 'siap diambil artinya apa?', 'pesanan saya siap diambil, lalu bagaimana?'],
  "Pesanan sudah siap di titik pengambilan. Anda bisa langsung mengambilnya.")

f([(T, "Status pesanan")],
  ["apa saja status pesanan?", "ada status apa saja di orders?", "status pesanan itu apa saja?", "sebutkan semua status pesanan"],
  "Status pesanan: Belum Dibayar, Belum Diambil, Siap Diambil, Selesai, dan Dibatalkan.")

f([(F, "Di mana saya mengambil pesanan?"), (A, "Lokasi pengambilan")],
  ["dimana saya mengambil pesanan?", "lokasi pengambilan dimana?", "ambil pesanannya di mana?", "titik pengambilan dimana ya?"],
  "Lokasi pengambilan ditentukan penjual dan bisa berubah. Lokasi pesanan Anda tampil di Checkout dan di halaman Detail Pengambilan.")

f([(F, "Jam berapa pesanan bisa diambil?"), (A, "Jadwal pengambilan")],
  ["jam berapa pesanan bisa diambil?", "kapan saya bisa ambil pesanan?", "jam pengambilan berapa?", "kloter itu apa?"],
  "Jam pengambilan dibagi menjadi kloter yang ditentukan penjual. Cek halaman Checkout untuk tanggal dan jam yang tersedia.")

f([(F, "Apa yang harus saya katakan saat mengambil pesanan?"), (A, "Saat mengambil pesanan")],
  ["bagaimana cara mengambil pesanan?", "apa yang harus dikatakan saat ambil pesanan?", "nomor pesanan saya dimana?", "saat ambil pesanan harus bilang apa?"],
  "Sebutkan nama atau nomor pesanan Anda kepada penjaga di titik pengambilan. Nomor pesanan ada di halaman Orders dan Detail Pengambilan.")

f([(F, "Saya tidak tahu rute ke titik pengambilan."), (A, "Petunjuk rute")],
  ["saya tidak tahu rute ke lokasi pengambilan", "ada petunjuk arah ke titik pengambilan?", "bagaimana menuju lokasi pengambilan?", "ada peta lokasinya?"],
  'Buka pesanan di tab Orders, lalu tekan "Buka Penunjuk Arah (Navigasi Maps)" atau "Buka di Google Maps".')

f([(F, "Di mana saya melihat pesanan saya?"), (A, "Cara mengecek pesanan")],
  ["dimana saya melihat pesanan saya?", "cara mengecek pesanan?", "riwayat pesanan dimana?", "pesanan aktif saya dimana?"],
  'Buka tab Orders. Tab "Pesanan Aktif" untuk pesanan yang berjalan, tab "Riwayat" untuk pesanan yang sudah selesai atau dibatalkan.')

f([(A, "Cara mengecek pesanan"), (T, "Status pesanan")],
  ["pesanan saya sudah siap belum?", "status pesanan saya apa?", "apakah pesanan saya sudah bisa diambil?", "pesanan saya sampai mana?"],
  'Saya tidak bisa melihat pesanan Anda secara langsung. Cek tab Orders: pesanan yang siap diambil berstatus "Siap Diambil" dan juga muncul di Home dengan tombol "Ambil".')

f([(F, "Pilihan apa saja yang bisa saya atur saat memesan?")],
  ["apa saja yang bisa diatur saat memesan?", "bisa pilih ukuran gelas?", "bisa atur tingkat manis?", "ada pilihan addon apa saja?"],
  'Anda bisa mengatur jumlah, ukuran gelas, dan tingkat manis. Opsi bisa berbeda untuk tiap menu, jadi lihat di lembar "Tambahkan Menu".')

f([(F, "Berapa tambahan biaya untuk ukuran Large?")],
  ["berapa tambahan biaya ukuran large?", "ukuran large nambah berapa?", "large lebih mahal berapa?", "biaya tambahan large berapa?"],
  'Sebagai contoh saat ini, Large (22 oz) menambah Rp 5.000 dan Reguler (16 oz) tanpa tambahan. Biaya pastinya tampil di lembar "Tambahkan Menu".',
  hanya_konteks=True)

f([(A, "Rincian biaya")],
  ["ada pajak nggak?", "apa saja biaya selain harga menu?", "biaya layanan berapa?", "kenapa total lebih mahal dari harga menu?"],
  "Total pesanan terdiri dari subtotal, pajak (saat ini 11% dari subtotal), dan biaya layanan (saat ini Rp 2.000). Nilai yang berlaku selalu tampil di Checkout.",
  hanya_konteks=True)

f([(F, "Bagaimana cara mencari menu?"), (T, "Fitur Home")],
  ["bagaimana cara mencari menu?", "dimana kolom pencarian?", "ada tombol search di home?", "cara cari kopi tertentu?"],
  'Pencarian ada di halaman Menu: ketik nama kopi di kolom "Cari kopi...". Halaman Home tidak punya tombol pencarian.')

f([(F, 'Kenapa muncul "menu tidak ada"?')],
  ["kenapa muncul menu tidak ada?", "menu yang saya cari tidak ketemu", "kok menunya tidak ada?", "menu tidak ditemukan, kenapa?"],
  'Menu yang Anda cari tidak ditemukan. Periksa penulisan nama menu, lalu coba lagi. Menu mungkin habis atau belum ditambahkan penjual. Untuk memastikan, tanyakan lewat tombol "Hubungi Penjual".')

f([(T, "(awal)")],
  ["ada halaman apa saja di aplikasi?", "menu di bagian bawah aplikasi apa saja?", "fitur navigasi apa saja yang ada?", "tombol keranjang dimana?"],
  "Ada empat menu navigasi di bagian bawah: Home, Menu, Orders, dan Profile. Ada juga tombol keranjang melayang yang menunjukkan jumlah item.")

f([(T, "Fitur Home")],
  ["apa saja isi halaman home?", "fitur di home apa saja?", "kartu siap diambil di home itu apa?", "menu favorit tetangga itu apa?"],
  'Home berisi banner event, kartu status pesanan yang siap diambil (dengan tombol "Ambil"), kategori cepat, Menu Favorit Tetangga, dan tombol "+" untuk menambah pesanan.')

f([(T, "Fitur Orders (Pesanan Saya)")],
  ["apa isi halaman orders?", "fitur orders apa saja?", "bedanya pesanan aktif dan riwayat apa?", "orders itu untuk apa?"],
  "Orders punya dua tab: Pesanan Aktif untuk pesanan yang belum selesai, dan Riwayat untuk pesanan Selesai atau Dibatalkan.")

f([(T, "Fitur Keranjang")],
  ["fungsi keranjang apa?", "bagaimana cara ke checkout?", "isi keranjang itu apa?", "keranjang untuk apa?"],
  "Keranjang berisi produk yang Anda pilih beserta addon-nya. Dari keranjang, Anda lanjut ke Checkout Pre-Order.")

f([(F, "Bagaimana cara menambah pesanan saat Checkout?")],
  ["bagaimana cara menambah pesanan saat checkout?", "mau tambah menu di checkout", "bisa ubah jumlah di checkout?", "tambah pesanan lain dimana?"],
  'Tekan "Tambah Pesanan Lain" di halaman Checkout. Anda juga bisa mengubah jumlah item dengan tombol minus dan plus.')

f([(F, "Kenapa saya tidak bisa memilih tanggal tertentu?")],
  ["kenapa tidak bisa pilih tanggal tertentu?", "tanggal yang saya mau tidak tersedia", "kok tanggalnya tidak bisa dipilih?", "kenapa tanggal tertentu tidak muncul?"],
  "Hanya tanggal yang disediakan penjual yang bisa dipilih. Tanggal lain tidak tersedia untuk pre-order.")

f([(F, "Bagaimana cara mengubah data profil?")],
  ["bagaimana cara mengubah data profil?", "cara edit profil?", "mau ganti nama di akun", "dimana edit profil?"],
  'Buka tab Profile, lalu pilih "Edit Profil".')

f([(F, "Bagaimana cara mematikan notifikasi?")],
  ["bagaimana cara mematikan notifikasi?", "cara matikan notifikasi?", "notifikasi terlalu banyak, cara mematikannya?", "dimana pengaturan notifikasi?"],
  'Buka tab Profile, lalu matikan tombol "Notifikasi".')

f([(F, "Bagaimana cara keluar dari akun?")],
  ["bagaimana cara keluar dari akun?", "cara logout?", "mau logout dimana?", "bagaimana cara keluar aplikasi?"],
  'Buka tab Profile, lalu tekan "Keluar".')

f([(F, "Bagaimana cara menghubungi penjual?"), (B, "Cara menghubungi penjual")],
  ["bagaimana cara menghubungi penjual?", "ada kontak penjual?", "mau chat penjual bisa?", "instagram yap coffee apa?"],
  'Tekan tombol "Hubungi Penjual" di Home atau Profile (membuka WhatsApp). Bisa juga lewat Instagram @yappcoffee.')

f([(N, "Bagaimana jika lupa kata sandi?")],
  ["saya lupa kata sandi, bagaimana?", "cara reset password?", "lupa password harus bagaimana?", "bagaimana cara mengatur ulang kata sandi?"],
  'Kata sandi bisa diatur ulang lewat kode OTP yang dikirim ke email Anda. Pilih "Lupa Password?" di halaman login, lalu ikuti langkahnya.')

f([(N, "Apakah pesanan bisa dibatalkan?")],
  ["bisa membatalkan pesanan?", "bagaimana cara batalkan pesanan?", "pesanan saya dibatalkan, kenapa?", "saya mau cancel pesanan"],
  'Pesanan bisa dibatalkan. Hubungi penjual lewat tombol "Hubungi Penjual" di Home atau Profile.')

f([(B, "Untuk siapa Yap Coffee?"), (B, "Masalah apa yang diselesaikan?")],
  ["yap coffee untuk siapa?", "apa keuntungan pakai aplikasi ini?", "kenapa harus pre-order?", "masalah apa yang diselesaikan yap coffee?"],
  "Yap Coffee dibuat untuk pelanggan yang ingin memesan kopi tanpa antre. Pesanan dibuat lebih dulu, lalu diambil sesuai jadwal.")

f([(B, "Platform")],
  ["ini aplikasi atau website?", "bisa dipakai di hp?", "yap coffee itu aplikasi mobile?", "platform yap coffee apa?"],
  "Yap Coffee adalah aplikasi seluler (mobile).")

f([(B, "Slogan dan ciri khas")],
  ["apa slogan yap coffee?", "yap coffee pakai kopi asli?", "apa ciri khas yap coffee?", "slogan aplikasi ini apa?"],
  'Slogan Yap Coffee: "Seduhan kopi berkarakter dengan harga bersahabat dan racikan khas Nusantara." Yap Coffee menyebut dirinya memakai 100% kopi asli dan aren.')

# cek semua sumber ada
hilang = [k for fk in FAKTA for k in fk["src"] if k not in BAGIAN]
if hilang:
    print("BAGIAN TIDAK DITEMUKAN (periksa judul di file .md):")
    for h in sorted(set(hilang)):
        print("  ", h)
    raise SystemExit(1)

# ---------- menu: harga diacak, hanya tabel ----------
def acak_harga(teks):
    out = []
    for b in teks.splitlines():
        if b.startswith("|") and "Rp" in b:
            b = re.sub(r"Rp\s?[\d.]+", lambda m: "Rp " + f"{random.randrange(12, 60) * 1000:,}".replace(",", "."), b)
        out.append(b)
    return "\n".join(out)

def baca_menu(teks):
    item, heading = {}, ""
    for b in teks.splitlines():
        if b.startswith("#"):
            heading = b.lower(); continue
        if "menu" not in heading or not b.startswith("|") or "---" in b:
            continue
        sel = [s.strip() for s in b.strip("|").split("|")]
        if len(sel) < 2 or sel[0].lower() == "menu":
            continue
        harga = next((s for s in sel[1:] if "Rp" in s), None)
        if harga:
            item[sel[0]] = harga
    return item

T_HARGA = ["berapa harga {m}?", "{m} harganya berapa?", "harga {m} berapa ya", "{m} berapa?", "mau tanya harga {m}"]
T_ADA = ["apakah ada {m}?", "{m} ada nggak?", "saya ingin memesan {m}, bisa?", "ada {m} tidak?", "bisa pesan {m}?"]
T_MANIS = ["apakah {m} manis?", "{m} rasanya manis nggak?", "seberapa manis {m}?"]
T_TIDAK_ADA = ["apakah ada menu {x}?", "{x} ada?", "saya mau pesan {x}", "jual {x} tidak?"]
TIDAK_ADA = ["nasi goreng", "mie goreng", "es teh", "jus alpukat", "bakso", "pizza", "burger",
             "boba", "kopi tubruk", "sate", "es krim", "teh tarik"]

LUAR = ["siapa presiden indonesia?", "ibukota jepang apa?", "buatkan kode python kalkulator",
        "berapa 12 x 15?", "siapa penemu lampu?", "ceritakan sejarah majapahit",
        "bagaimana cara membuat website?", "apa itu machine learning?", "prediksi cuaca besok",
        "siapa juara piala dunia 2018?", "terjemahkan ke inggris: selamat pagi",
        "tolong ceritakan lelucon", "bagaimana cara menjadi kaya?", "rekomendasi film bagus"]

TIDAK_TAHU = ["jam buka yap coffee berapa?", "kapan penjual buka?", "jam operasional penjual?",
              "bisa pesan untuk hari ini juga?", "apakah bisa pesan di hari yang sama?",
              "kalau lewat 10 menit belum bayar bagaimana?", "pesanan hangus kalau telat bayar?",
              "ada program poin atau member?", "ada kartu member?", "berapa nomor whatsapp penjual?",
              "alamat email penjual apa?", "kode otp tidak masuk bagaimana?", "otp tidak terkirim ke email saya",
              "apakah ada cabang lain?", "bisa pesan untuk acara besar?", "ada menu vegan?",
              "berapa kalori es kopi susu?", "apakah bisa refund?", "apakah aplikasinya ada di ios?",
              "bisa bayar pakai kartu kredit?"]

SAPA = ["halo", "haloo", "hai", "selamat pagi", "selamat siang", "apa kabar?", "hi kak"]
JAWAB_SAPA = ["Halo! Selamat datang di Yap Coffee. Ada yang bisa saya bantu?",
              "Hai! Saya asisten Yap Coffee. Mau tanya soal menu atau pemesanan?"]

# ---------- rakit ----------
data = {}   # json -> split
def tambah(split, e):
    data.setdefault(json.dumps(e, ensure_ascii=False), split)

for fk in FAKTA:
    qs = fk["qs"]
    for i, q in enumerate(qs):
        split = "eval" if (i == len(qs) - 1 and len(qs) >= 4) else "train"
        for _ in range(2):
            tambah(split, ex(susun(MENU, fk["src"], random.choice([0, 1])), aug(q), fk["a"]))
        if not fk["hanya_konteks"]:
            tambah(split, ex(susun(MENU, [], random.choice([1, 2])), aug(q), fk["a"]))

def acak_split():
    return "eval" if random.random() < 0.1 else "train"

for _ in range(200):                       # menu & harga (RAG)
    menu_acak = acak_harga(MENU)
    item = baca_menu(menu_acak)
    if not item:
        continue
    m = random.choice(list(item)); r = random.random()
    k = susun(menu_acak, [], random.choice([0, 1, 2]))
    if r < 0.4:
        tambah(acak_split(), ex(k, aug(random.choice(T_HARGA).format(m=m)), f"Harga {m} adalah {item[m]}."))
    elif r < 0.7:
        tambah(acak_split(), ex(k, aug(random.choice(T_ADA).format(m=m)), f"Ada, {m} tersedia di menu dengan harga {item[m]}."))
    elif r < 0.85:
        tambah(acak_split(), ex(k, aug(random.choice(T_MANIS).format(m=m)), "TIDAK_TAHU"))
    else:
        tambah(acak_split(), ex(k, aug(random.choice(T_TIDAK_ADA).format(x=random.choice(TIDAK_ADA))), "TIDAK_TAHU"))

for q in LUAR:                              # di luar topik
    for _ in range(4):
        tambah(acak_split(), ex(susun(MENU, [], random.choice([1, 2])), aug(q), "TIDAK_RELEVAN"))

for q in TIDAK_TAHU:                        # berkaitan tapi tidak ada datanya
    for _ in range(3):
        tambah(acak_split(), ex(susun(MENU, [], random.choice([1, 2])), aug(q), "TIDAK_TAHU"))

for q in SAPA:                              # sapaan
    for _ in range(2):
        tambah(acak_split(), ex(susun(MENU, [], random.choice([0, 1])), q, random.choice(JAWAB_SAPA)))

train = [k for k, s in data.items() if s == "train"]
ev = [k for k, s in data.items() if s == "eval"]
random.shuffle(train); random.shuffle(ev)
with open("train.jsonl", "w", encoding="utf-8") as fo:
    fo.write("\n".join(train) + "\n")
with open("eval.jsonl", "w", encoding="utf-8") as fo:
    fo.write("\n".join(ev) + "\n")
print(f"latih: {len(train)}, uji: {len(ev)}")