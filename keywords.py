# keywords.py
# =============================================================================
# CogniFi — Keyword Banks untuk Deteksi Bias Investasi
# =============================================================================
#
# File ini berisi SEMUA daftar kata kunci yang dipakai bias_detector.py.
# Dipisah ke sini supaya:
#   1. Mudah ditambah/edit tanpa menyentuh logika deteksi
#   2. Bisa di-review secara independen saat akurasi turun
#   3. Jelas mana yang kata kunci, mana yang logika
#
# CARA EDIT:
#   - Cukup tambah/hapus string di list yang sesuai
#   - Semua huruf kecil (lowercase) — matching dilakukan di text.lower()
#   - Hindari kata terlalu pendek/umum (mis. "oke", "bagus") tanpa konteks
#   - Setelah edit, jalankan: python test_bias_accuracy.py
#
# STRUKTUR FILE:
#   BAGIAN 1 — FOMO              (FOMO_URGENCY, FOMO_SOCIAL)
#   BAGIAN 2 — LOSS AVERSION     (DENIAL, AVERAGING, BLAME)
#   BAGIAN 3 — CONFIRMATION BIAS (LEADING, ECHO, POSITIVE, OVERCONFIDENT)
#   BAGIAN 4 — NETRAL / OVERRIDE (RISK, ANALYSIS, EDUCATION, ANALYTICAL)
#
# =============================================================================


# =============================================================================
# BAGIAN 1 — FOMO (Fear of Missing Out)
# Sinyal: user takut ketinggalan momentum atau harga naik
# =============================================================================

# --- FOMO_URGENCY ---
# Kata kunci urgensi masuk, timing, momentum naik, dan hype.
FOMO_URGENCY = [

    # Eksplisit FOMO — langsung menyebut ketakutan ketinggalan
    "fomo", "takut ketinggalan", "ketinggalan", "kelewatan",
    "telat", "terlambat", "udah telat", "jangan telat",
    "buru-buru", "buruan", "buruan masuk",
    "ga boleh dilewatin", "jangan dilewatin", "jangan ketinggalan",
    "jangan sampe ketinggalan", "peluang langka",
    "sayang kalau miss", "miss momentum", "sayang kalau kelewatan",
    "harus masuk hari ini", "sebelum naik lagi", "sebelum terlambat",
    "cuma ada waktu", "waktu sedikit",
    "beli balik", "beli lagi ga mau miss", "mau beli lagi", 
    "jual terlalu cepat", "nyesal jual", "seharusnya ga jual",
    "sekarang atau tidak", "sekarang atau ga sama sekali",
    "kalau ga sekarang kapan lagi", "kapan lagi kalau bukan sekarang",
    "takut kehabisan", "kehabisan momentum", "kehabisan kesempatan",
    "kalau masih lanjut", "masih lanjut gimana", "kalau lanjut naik",

    # ── Entry action slang baru ───────────────────────────────────
    "masuk sini", "masuk aja", "masuk sini soalnya",
    "entry cepat", "cepat entry", "keburu naik",
    "jual yang lain masuk", "jual masuk",
    "alihkan dana", "pindahkan dana",
    "serbu!!!",  "serbu", "siapp komandan",  # battle cry FOMO
    "wujudkan mimpi kita",  # collective aspiration FOMO
    "kesempatan kaya mendadak",  # opportunity FOMO
    "konglo hapsoro", "sultan djoni",  # konglo social proof FOMO
    "masa ga bisa multibagger",  # FOMO framing via konglo
    "pompom waran", "siap-siap jam",  # coordinated FOMO
    "kalian yang suka ngejar pucuk",  # FOMO description
    "bisa ara oleh bandar kan",  # bandar FOMO trigger
    "buruan cutlos sebelum senin",  # FOMO selling urgency
    "buruan depo sekarang",  # FOMO urgency deposit
    "semakin turun semakin banyak berani buy",  # buy the dip FOMO
    "pernah terbang ke 3100", "pernah terbang ke",  # price anchor FOMO

    # ── Slang khusus batch baru ───────────────────────────────────
    "haka aja", "haka lah", "haka buat",
    "gas kan lah", "gas kan aja",
    "akhirnya bangkit",
    "masih ikut naik",
    "running trade", "cp beli nego",
    "siapkan dana kabarnya",
    "bapak prajogo", "prajogo pangestu",
    "akan ipo segera", "ipo segera", "akan ipo",
    "realistis atau ngimpi",
    "psikologi ritel",
    "ritel panik saat merah",

     # ── Batch baru FOMO patterns ─────────────────────────────────
    "rungkatin para investor",          # FOMO fear pump
    "dibuat floating loss 100%",        # FOMO pump warning
    "turunkan ke 3500",                 # FOMO buy the dip
    "dosen killer mei msci",            # FOMO event urgency
    "saham2 konglo yang recovery",      # FOMO opportunity
    "kesempatan kaya mendadak",
    "wujudkan mimpi kita",
    "bid gede siap turun sayangi uang kalian gaess buruan",  # [980]
    "apakah mbg mau ipo", "mbg mau ipo",                     # [987]
    "siap-siap jam", "siap2 jam",                            # coordinated FOMO
    "pompom waran",
    "semakin turun semakin banyak berani buy",
    "serbu", "siapp komandan",
    "baru masuk kemren 50 malah disuruh buang",  # [902]
    "kalau haka tadi pas saya notice masih dapat cuan",  # timing FOMO
    "di taikin dulu supaya pada percaya",  # [894] pump narrative
    "lot match done ada yang haka di angka arb",  # [895]
    "sayangi uang kalian gaess buruan cutlos sebelum",  # [980]

    # ── Contrarian FOMO / opportunistic buy ──────────────────────
    "serakahlah saat", "serakah saat orang lain takut",
    "takutlah saat orang lain serakah",
    "saat orang lain takut beli",
    "beli saat orang panik",

    # ── Momentum teknikal implisit ────────────────────────────────
    "jebol lagi", "semoga jebol", "jebol ke atas",
    "batas profit 200", "profit 200%", "target profit 200",
    "saham beger",                    # saham bergerak = momentum play
    "perkiraan ihsg", "ihsg bergerak",
    "saham yang dapat diperhatikan",  # watchlist = FOMO selection
    "saham2 yg dapat di perhatikan",

    # ── FOMO aspirasional / realistis ────────────────────────────
    "ngimpi tapi mungkin", "realistis atau ngimpi",
    "ini realistis", "ngimpi ga sih",
    "masih mungkin", "kan presidennya masih",
    "pasti bisa naik karena punya",   # appeal to authority = FOMO
    "punya adiknya", "punya anaknya prabowo", "punya presiden",

    # ── FOMO dari prospektus / IPO ───────────────────────────────
    "waktu prospektus harga", "harga prospektus",
    "dari prospektus ke sekarang",

    # ── Jangan panik + konteks bullish = FOMO rationalization ────
    "jangan panik hanya karena", "jangan panik karena",
    "jangan panik tapi laba",
    "laba pertahun masih naik", "laba tahunan masih",

    # ── Rotasi saham = FOMO entry baru ───────────────────────────
    "jual yang lain masuk", "jual yang lain, masuk",
    "masuk ssia", "masuk ke ssia",

    # ── Doa / ekspresi masuk saham ───────────────────────────────
    "bismillah",          # berdiri sendiri = doa sebelum entry

    # ── Catalyst + timing FOMO ───────────────────────────────────
    "beberapa hari sebelum", "sebelum perang", "sebelum event",
    "menjelang lebaran", "menjelang dividen", "menjelang ex-date",
    "sebelum msci", "msci announcement", "calon msci", "calon kuat msci",

    # ── Sinyal teknikal bullish implisit ─────────────────────────
    "hilal udah kelihatan", "hilal kelihatan",
    "besok harusnya hijau", "harusnya hijau",
    "siap siap diguyur", "diguyur lagi", "bakal diguyur",
    "berpotensi hit", "potensi hit",
    "keburu naik", "arb ",              # arbitrage peluang naik

    # ── Slang dialek ─────────────────────────────────────────────
    "arakeun",            # Sunda: ARA-kan (harap ARA)
    "arra",               # typo ARA

    # ── Scarcity / urgensi stok ──────────────────────────────────
    "barang yu habis", "habis itu barang", "barang habis",
    "siapkan dana", "siap-siap dana",
    "wajib lock", "lock dulu",

    # ── Social call to action ─────────────────────────────────────
    "join yuk", "join dong",
    "to the moon",
    "bull run", "prepare for another bull",
    "bau bullist", "bau bullish", "bau mau naik",

    # Entry action slang
    "entry cepat", "masuk sini", "masuk aja sekarang",
    "alihkan dana", "pindahkan ke", "jual yang lain masuk",
    "siapkan dana", "wajib lock", "lock dulu",
    "join yuk", "join dong", "beli terus sekarang",

    # Ekspresi doa/semangat masuk saham  
    "bismillah",          # standalone = doa sebelum entry
    "to the moon",
    "bull run", "prepare for",

    # Scarcity / barang habis
    "barang habis", "barang yu habis", "keburu naik",
    "keburu abis", "keburu ditinggal",

    # Slang dialek ARA
    "arakeun",            # Sunda = "ARA-kan"
    "arra",               # typo ARA

    # Market bullish implisit
    "bau bullist", "bau bullish", "bau mau naik",
    "besok harusnya hijau", "ihsg bakal hijau",
    "diguyur lagi",       # bandar bakal pompa = FOMO
    "potensi hit",        # upcoming catalyst
    "hilal udah kelihatan",  # idiom = sinyal naik
    "berpotensi",

    # Social proof via profit orang lain
    "nyantol dipuncak",   # orang lain beli mahal = naik
    "prepare for another",

    # Entry / timing — kapan masuk, apakah masih aman
    "masuk sekarang", "entry sekarang", "beli sekarang",
    "mau masuk", "sempet masuk", "masih sempet", "masih sempet masuk ga",
    "masih aman masuk", "aman masuk ga",
    "right time to enter", "right time to buy", "right time to get in",
    "sinyal kuat kan", "ini sinyal kuat",
    "kapan masuk", "masih worth it", "worth it ga", "worth ga",
    "timing masuk", "timing entry", "timing oke", "timing bagus",
    "timing tepat", "timing yang pas", "timing pas",
    "ini timing", "kira-kira timing", "timing masuk yang tepat",
    "ini momen", "momen masuk", "momen beli", "momen cuan",
    "too late already", "too late to buy", "is it too late",
    "still worth buying", "worth buying now",
    "ga mau miss", "sayang kalau ga masuk", "sayang banget kalau ga masuk",
    "sebelum makin tinggi", "sebelum naik lagi", "rugi kesempatan",
    "biar ga rugi kesempatan",

    # Sinyal teknikal bullish
    "sinyal masuk", "sinyal beli", "sinyal kuat buat masuk",
    "lagi breakout", "udah breakout", "mau breakout", "baru breakout",
    "breaking out", "bullish", "lagi naik", "naik terus", "naik kenceng",
    "mau naik", "naik tinggi", "pasti bakal balik", "yakin bakal balik",
    "volume naik", "volume tinggi", "volume gede", "volume naik gila",
    "volume tinggi banget", "ada berita bagus", "mungkin ada berita",

    # Hype / slang pasar — Stockbit, Telegram, TikTok Finance
    "pump nih", "mau pump", "bakal pump", "pump incoming",
    "about to pump", "about to moon", "about to explode", "about to run",
    "going to pump", "mooning", "flying",
    "moon", "to the moon", "terbang", "terbang tinggi",
    "ngegas", "lagi ngegas", "gaspol",
    "moodeng effect", "rally", "baru awal", "awal rally",
    "rame banget", "trending", "viral di stockbit", "viral nih",
    "hype", "euforia",

    # FOMO implisit dari profit teman / portofolio hijau
    "cuan gede", "cuan nih", "cuan banget",
    "profit gede", "profit 30%", "profit minggu lalu",
    "naik 20%", "naik seminggu",

    # Feeling / intuisi bullish
    "feeling kuat", "feeling bagus", "feeling positif",
    "keliatannya oke", "keliatannya bagus", "prospeknya oke", "kayaknya oke",

    # Aksi masuk impulsif
    "yolo", "all in", "ikutan", "ikut dong", "mau coba juga",
    "mau tambah posisi", "right time to enter", "right time to buy", 
    "right time to get in",

    # Regret-driven FOMO — pernah jual terlalu cepat, sekarang mau masuk lagi
    "dulu jual terlalu cepat", "jual terlalu cepat", "nyesel jual",
    "sebelum makin tinggi", "beli balik sebelum", "takut nyesel lagi",

    # English
    "don't miss", "don't miss out", "missing out",
    "buy now", "get in now", "should i get in",
    "still good to buy", "seems like it's breaking",
    "looks like it's about to",

    # ── Slang Stockbit / Twitter / Telegram ──────────────────────────
    # Auto Reject Atas & momentum ekstrem
    # CATATAN: "ara" harus dipadded spasi agar tidak match "c-ARA", "anal-ISIS", "sek-ARANG"
    " ara ", "ara!!",      # ARA sebagai kata sendiri, bukan substring
    "auto reject atas", "ndar", "auto reject bawah",
    "gass", "gas", "gasss", "gaskiw", "gaskeun", "gaspol",
    "mantap", "top gainers", "masuk top gainers",
    "jebol resistance", "jebol ke", "breakout nih", "udah breakout",

    # ── Slang khusus batch baru ───────────────────────────────────
    "haka aja", "haka lah", "haka buat",         # "haka aja lumayan buat thr" = masuk FOMO
    "gas kan lah", "gas kan aja",
    "akhirnya bangkit",                           # "$PACK akhirnya bangkit" = momentum
    "masih ikut naik",                            # "$OILS senin masih ikut naik" = FOMO
    "running trade",                              # "di running trade" = momentum entry
    "cp beli nego",                               # CP beli nego = sinyal bandar = FOMO entry
    "siapkan dana kabarnya",                      # "siapkan dana kabarnya IPO" = FOMO IPO
    "bapak prajogo", "prajogo pangestu",          # nama trigger FOMO saham
    "akan ipo segera", "ipo segera", "akan ipo",
    "realistis atau ngimpi",                      # "ini realistis?" = ekspektasi bullish
    "digoreng habis-habisan",
    "psikologi ritel",                            # "psikologi ritel" = edukasi tentang FOMO
    "ritel panik saat merah",                     # "ritel panik = FOMO exit" = observasi FOMO


    # Ajakan masuk komunal
    "ayo siap-siap", "ayo masuk", "siap-siap", "ready masuk",
    "mari masuk", "mari berinvestasi", "yuk masuk", "yuk beli",
    "jangan sampai miss", "sayang kalau miss", "sayang kalau ga masuk",

    # Regret / miss sebelumnya → masuk sekarang
    "miss pump", "dua kali miss", "berkali-kali miss", "pernah miss",
    "nyesal miss", "ga mau miss lagi", "kali ini ga mau ketinggalan",
    "kapan lagi harga segini", "kapan lagi bisa beli",

    # Market bullish / IHSG naik = FOMO trigger
    "market luar hijau", "market hijau", "ihsg lanjut naik",
    "ihsg ijo", "market rebound", "market recovery",
    "semoga ihsg", "moga ihsg", "besok ijo", "besok naik",
    "lanjut naik", "lanjut rally", "rebound nih",

    # Volume / aktivitas tidak biasa
    "volume jumbo", "volume gila", "volume meledak",
    "tiba-tiba volume", "ada apa di", "kenapa volume",

    # Sinyal teknikal bullish slang
    "mantul dari support", "balik ke atas", "mulai mantul",
    "finally naik", "finally mantul", "finally breakout",
    "akhirnya naik", "akhirnya mantul",

    # Full cash / ketinggalan pasar
    "full cash", "ga ada porto", "gaada porto",
    "masih di cash", "duduk di cash",
    "ganti saham", "switch ke", "jual masuk",

    # Murah banget = FOMO entry
    "murah banget", "udah murah banget", "harga udah murah",
    "murah sekali", "harga cuci gudang",
]

# --- FOMO_SOCIAL ---
# Pengaruh orang lain / komunitas / influencer sebagai pendorong beli.
# Beda dengan FOMO_URGENCY: ini soal "orang lain", bukan "waktu/momentum".
FOMO_SOCIAL = [

    # Referensi teman / orang sekitar
    "temen gua", "temen gue", "teman gue", "temen saya",
    "temen profit", "semua temen",
    "teman-teman", "teman teman",
    "dia udah masuk", "dia udah profit", "dia rekomen",

    # Social proof massal
    "semua orang", "semua orang pada", "semua pada beli",
    "pada beli", "pada masuk", "pada cuan", "pada profit",
    "semua hijau", "semua orang fomo", "semua lagi beli",
    "ribuan orang", "banyak orang bahas",

    # Komunitas / grup / forum
    "di grup", "di komunitas", "grup saham",
    "semua di grup", "komunitas bilang",
    "di forum", "semua forum", "rame dibahas",
    "trending di stockbit", "viral di", "rame di",
    "di semua platform", "semua platform",
    "channel youtube", "youtube saham", "buzz di", "sosmed",
    "ramai dibicarain", "grup wa", "wa saham",
    "semua channel", "channel youtube", "youtube saham",
    "buzz di sosmed", "buzz di", "sosmed", "ramai dibicarain",
    "viral di youtube", "ramai dibahas di",
    "pembelian berdasarkan screenshot", "beli karena tweet",
    "beli karena posting", "beli karena kabar",

    # Influencer / analis sebagai trigger
    "kata influencer", "influencer bilang", "influencer favorit",
    "kata si ", "kata orang", "analis juga bilang", "analis bilang bagus",

    # English
    "everyone is buying", "everyone's buying", "everyone's talking",
    "all my friends", "my friends are", "friends are making",
    "making money on", "profiting from",
    "people are buying", "people are making money",

    # ── Slang komunitas Stockbit / Telegram ──────────────────────────
    # Referensi komunitas / orang lain cuan
    "yang serok", "yang beli", "yang masuk", "yang udah masuk",
    "yang udah beli", "yang pegang",
    "pasti senyum-senyum", "pasti cuan", "pasti untung",
    "orang lain beli murah", "dibeli murah orang",

    # Anti-fear framing = implisit FOMO
    "jangan termakan fear", "jangan takut", "jangan panik jual",
    "jangan ikut panic sell", "selama masih pegang",
    "king masih buy", "big player masih buy",
]


# =============================================================================
# BAGIAN 2 — LOSS AVERSION
# Sinyal: user menghindari cut loss, averaging down, atau menyalahkan luar
# =============================================================================

# --- LOSS_AVERSION_DENIAL ---
# Penolakan merealisasi kerugian: hold terus, rasionalisasi, nunggu balik modal.
LOSS_AVERSION_DENIAL = [

    # Penolakan cut loss eksplisit
    "nyangkut", "nyangkut parah", "floating loss",
    "belum mau cut loss", "ga mau cut loss", "gak mau cut loss",
    "kagak mau", "kagak mau cut", "turun dari puncak",
    "porto merah", "porto gue merah", "portofolio gue merah",
    "semua porto merah", "jual rugi", "rugi kalau jual", "masa mau jual rugi",
    "ga mau realized", "belum direalisasi", "belum realize", "unrealized",
    "sayang banget kalau jual", "ga sanggup jual", "gak sanggup jual",
    "too painful to sell", "painful to sell", "sakit kalau jual",
    "tahan posisi", "pertahankan posisi",
    "gue tahan",  # explicit hold under loss
    "holder avg", "holder avg 230", "holder avg up",  # holder anchoring
    "masih bisa makan kan",  # dark humor holding at loss
    "berharap recovery modal",  # hope recovery = LA
    "smoga kita cuan bareng",  # solidarity hoping recovery
    "semangat guys refreshing gausa liatin porto",  # avoidance
    "pasti akan recovery",  # conviction hold = LA
    "recovery porto gua", "lama ini recovery porto",
    "diguyur setiap hari float loss",  # frustrated hold
    "terlalu banyak asing posisinya floating loss",
    "kuncinya bisa sabar atau tidak menunggu recovery",
    "loss 30jtan di kripto sisa dana",  # LA displacement

    # ── Anti-CL / menahan diri tidak jual ────────────────────────
    "anti cut loss", "anti cl", "anti cutloss",
    "anti cut lost",
    "ga bakal cl", "gaakan cl", "gaakan cutloss", "gaakan jual",
    "ga akan cl", "tidak akan cl",
    "menahan diri untuk tidak cl", "menahan diri buat ga cl",
    "menahan diri untuk tidak cut loss",
    "menahan diri buat tidak cut loss",
    "tahan untuk tidak cut loss", "tahan buat ga cl",
    "mau dibanting sedalem", "dibanting sedalem apapun",
    "sedalem apapun ga", "sedalem apapun gak",
    "ga cl deh", "gak cl deh", "engga cl",
    "belum cl", "belum cutloss dulu",
    "ga mau cl", "gak mau cl",
    "mau dibiarin aja", "biarin aja dulu",
    "bodo amat ampe", "bodo amat sampe",
    "sampe taun depan", "ampe tahun depan",
    "mau hold dulu aja", "biar aja dulu",

    # ── Ekspresi minus / kerugian implisit ───────────────────────
    "balikin loss", "cara balikin", "gimana balikin",
    "mines saja", "angka mines", "angka minus",
    "itukan angka mines", "itu angka mines",
    "belum cutloss itukan", "selama belum cutloss",
    "minus 80%", "minus 56", "minus 21", "minus 26",
    "minus 20%", "minus 15%", "minus 6%",
    "nangeeeess", "nangeeess", "nanges", "nangis",

    # ── Uninstall / kabur dari platform ──────────────────────────
    "uninstall stockbit", "uninstal stockbit",
    "hapus stockbit", "delete stockbit",
    "ga buka stockbit", "ga berani buka",
    "ga buka aplikasi", "ga berani lihat porto",
    "jangan dilihat makin", "jangan dilihat",

    # ── Sarkasme / dark humor tetap LA ───────────────────────────
    "optimis terjun ke inti bumi",
    "optimis, iya optimis terjun",
    "terjun ke inti bumi",
    "cl rugi sl rugi semua rugi",
    "cl rugi sl rugi",
    "semua rugi bgstt", "semua rugi bgs",
    "mau cutloss sayang mau hold",
    "mau cutloss sayang",
    "hanya pengecut yang", "pengecut yang melakukan cutloss",

    # ── Dana dingin / rasionalisasi ──────────────────────────────
    "dana dingin", "uang dingin",
    "dana dingin better di hold", "uang dingin hold",
    "nyimpen dana dingin", "nyimpen uang dingin",
    "stop main saham", "anggap stop main",

    # ── Tetap hold meski hopeless ─────────────────────────────────
    "ga sanggup hold lagi", "udah ga sanggup hold",
    "kalo cl bisa rugi banyak", "kalau cl bisa rugi",
    "hold sampai kiamat", "masih hold sampai kiamat",
    "ga bisa cl", "tidak bisa cl",
    "sementara ga cl dulu", "ga cl dulu kecuali",
    "race to the bottom",
    "kalau makin ditambah", "makin ditambah jadi",
    "rugi itu belum ada", "jangan pernah salahkan",
    "adro kena sl", "kena sl tapi",
    "pasar saham naik besok", "ada pepatah",
    "akhir tahun balik", "balik lagi akhir",

    # ── Ovt / overthinking ────────────────────────────────────────
    "ga ovt", "gak ovt", "ga overthinkin",
    "ga overthinking", "tidak ovt",

    # ── Ekspresi humor / sarkasme yang tetap LA ──────────────────
    "icikiwir",                           # ekspresi hopeful Jawa = tetap pegang
    "mindset belum dijual belum rugi",
    "selama belum dijual masih belum rugi",
    "belum dijual belum rugi",
    "paper loss",

    # ── Tunggu diskon ekstrem (dark humor LA) ────────────────────
    "tunggu diskon 90", "tunggu diskon 99", "tunggu diskon",
    "nunggu 99%", "nanggung nunggu",
    "masih nunggu",

    # ── Tetap hold meski stop loss / cut loss ────────────────────
    "kena sl tapi beli lagi", "sl tapi buy lagi",
    "cutloss berkali2 tetap", "meski sudah cutloss tetap",
    "abis cl tetap", "abis modal tapi tetap tahan",
    "minggu kemaren cl tapi tetap",

    # ── Contrarian averaging / tambah muatan ─────────────────────
    "saatnya tambah muatan", "tambah muatan disaat",
    "disaat retail lain menyerah", "saat orang lain menyerah",
    "retail menyerah",

    # ── Tetap pegang / hold emosional ────────────────────────────
    "tetap aku pegang", "tetap deh", "tetap pegang deh",
    "masih tetap pegang", "saham kesayangan",
    "mengkultuskan",                      # kultus saham = LA emosional
    "berdoa utk yang udah masuk tetap tahan",

    # ── Rationalisasi minus / tidak cut loss ─────────────────────
    "minusnya sudah turun", "semoga besok makin turun minusnya",
    "merah akhir tahun sudah hijau", "sekarang merah nanti hijau",
    "makin anjlok makin", "makin turun makin",   # "makin turun makin terasa yield"
    "dividen yield makin", "yield makin jumbo",
    "saya malah ingin",

    # ── Holder hopeful ───────────────────────────────────────────
    "jangan exit dulu bentar lagi", "bentar lagi meroket",
    "holder X kalo jangan exit",
    "gua juga holder", "juga holder",
    "main cacing naga",                   # slang = nyangkut dalam

    # Ekspresi humor/sarkasme yang tetap LA
    "icikiwir",                    # ekspresi hopeful Jawa
    "mindset belum dijual belum rugi",
    "selama belum dijual masih belum rugi",
    "belum dijual belum rugi",
    "paper loss",                  # istilah teknis LA

    # Tetap hold meski CL/SL
    "kena sl tapi buy lagi", "cutloss tapi beli lagi",
    "tetap beli lagi", "meski cutloss tetap",
    "abis cl tetap", "abis modal tapi tetap",

    # Tunggu diskon ekstrem (dark humor LA)
    "tunggu diskon 90", "tunggu diskon 99",
    "nunggu 99%", "nanggung nunggu",
    "tunggu rugi lebih dalam",

    # Contrarian averaging
    "saatnya tambah muatan", "tambah muatan saat",
    "disaat retail lain menyerah", "saat orang lain menyerah",
    "tetap pegang deh", "tetap aku pegang",
    "mengkultuskan",               # kultus saham = LA emosional

    # Hold hopeful
    "bentar lagi meroket", "jangan exit dulu bentar lagi",
    "holder X kalo jangan exit",
    "cutloss berkali2 tetap beli",

    # Hold / tunggu
    "hold dulu", "hold aja", "hold terus", "hold keras",
    "tahan dulu", "simpan dulu", "tetap hold", "kekeuh hold",
    "tetap kekeuh", "keras hold",
    "sabar aja", "tunggu dulu", "mending tunggu",
    "holding on", "just wait", "just holding",
    "long term hold", "holding long term",
    "ga mau jual", "gak mau jual", "tidak mau jual",
    "merah semua", "porto merah", "portofolio merah",
    "terlanjur", "udah terlanjur",
    "deep in red", "underwater",
    "cuma sentimen", "sentimen negatif doang", "bukan sentimen",
    "bukan salah sahamnya", "bukan salah perusahaan",
    "convinced", "convinced recovery",
    "sabar nunggu harga", "nunggu harga balik",
    "nunggu dividen", "dividen nutupin",

    # Nunggu break even
    "nunggu balik modal", "balik modal dulu",
    "break even", "balik ke break even", "nunggu break even",
    "waiting to break even",

    # Stuck / terjebak posisi
    "stuck di", "i'm stuck", "masih stuck",
    "HPP", "harga pokok pembelian", "turunin HPP",
    "minus dalam", "minus parah", "minus banyak",

    # Keyakinan rebound
    "pasti balik", "pasti naik lagi", "pasti rebound",
    "nanti juga naik", "bakal balik", "akan balik",
    "bounce back", "will bounce back", "will recover", "will come back",

    # Rasionalisasi koreksi
    "ini cuma koreksi", "cuma koreksi", "koreksi sementara",
    "cuma noise", "noise pasar", "sementara aja",
    "jangka panjang pasti bagus", "jangka panjang pasti naik",
    "ini investasi jangka panjang", "long term pasti",
    "masih dalam support", "support kuat", "jangka panjang pasti untung",
    "long term pasti bagus",
    "fundamental aman", "fundamental masih bagus", "masih bagus kok",
    "ga perlu khawatir",
    "just a correction", "just a dip", "just noise",

    # Istilah kapitulasi / panik
    "panic sell", "panic cutloss", "cutloss panik",
    "auto cutloss", "auto jual", "capitulation", "udah jeblos",

    # English
    "won't sell at a loss", "will not sell",

    # ── Slang Stockbit / Twitter ──────────────────────────────────────
    # Penolakan jual dalam kondisi minus
    "sayang banget kalau jual", "sayang jual", "sayang banget jual",
    "susah jualnya", "susah jual", "ga tegaan jual",
    "belum ikhlas jual", "ga ikhlas jual",
    "simpan buat kenang-kenangan", "kenang-kenangan",
    "ga peduli rugi", "gak peduli rugi", "gak peduli mau rugi",
    "gak peduli delisting", "gak peduli bangkrut",
    "terima nasib", "pasrah aja",

    # Ga bakal jual variants
    "ga bakal jual", "tidak bakal jual", "ga akan jual",
    "ga mau jual di bawah", "jual di bawah avg", "di bawah avg",
    "ga bakal jual selama",

    # Minus eksplisit + hold
    "minus 30", "minus 27", "minus 20", "minus 15", "minus 10",
    "minus banyak tapi", "udah minus tapi",
    "bertahun-tahun minus", "bertahun tahun",
    "belum ekstrem", "belum turun ekstrem", "minus belum ekstrem",
    "investor hold", "hold bukan jual",

    # Averaging down slang
    "stay avg", "avg masih", "haka", "haka di",
    "cl atau avgd", "cut loss atau average",
    "avgd atau cl",

    # Rationalisasi jangka panjang
    "buat anak", "buat nanti", "utk nanti", "buat jangka panjang",
    "nabung saham", "nabung di saham",
    "ga mau jual di bawah avg", "jual di bawah avg",

    # Regret hold / tidak jual
    "tau gitu hold", "tau gitu ga jual", "seharusnya ga jual dulu",
    "belum putar balik", "belum recovery",

    # ── Anti-CL / menahan diri tidak jual ────────────────────────
    "anti cut loss", "anti cl", "anti cutloss",
    "anti cut lost",                          # typo umum
    "ga bakal cl", "gaakan cl", "gaakan cutloss", "gaakan jual",
    "ga akan cl", "tidak akan cl",
    "menahan diri untuk tidak cl", "menahan diri buat ga cl",
    "menahan diri untuk tidak cut loss",
    "menahan diri buat tidak cut loss",
    "tahan untuk tidak cut loss",
    "tahan buat ga cl",
    "mau dibanting sedalem", "dibanting sedalem apapun",
    "sedalem apapun ga", "sedalem apapun gak",
    "ga cl deh", "gak cl deh", "engga cl",
    "belum cl", "belum cutloss dulu",
    "ga mau cl", "gak mau cl",
    "mau dibiarin aja", "biarin aja dulu",
    "bodo amat ampe", "bodo amat sampe",
    "sampe taun depan", "ampe tahun depan",
    "sampai tahun depan bodo",
    "mau hold dulu aja", "biar aja dulu",

    # ── Ekspresi minus / kerugian implisit ───────────────────────
    "balikin loss", "cara balikin", "gimana balikin",
    "mines saja", "angka mines", "angka minus",
    "itukan angka mines", "itu angka mines",
    "belum cutloss itukan", "selama belum cutloss",
    "minus 80%", "minus 56", "minus 21", "minus 26",
    "minus 20%", "minus 15%", "minus 6%",
    "nangeeeess", "nangeeess", "nanges",
    "nangis",                                 # ekspresi kerugian

    # ── Uninstall / kabur dari platform ──────────────────────────
    "uninstall stockbit", "uninstal stockbit",
    "hapus stockbit", "delete stockbit",
    "ga buka stockbit", "ga berani buka",
    "ga buka aplikasi", "ga berani lihat porto",
    "jangan dilihat makin", "jangan dilihat",

    # ── Sarkasme / dark humor tetap LA ───────────────────────────
    "optimis terjun ke inti bumi",
    "optimis, iya optimis terjun",
    "terjun ke inti bumi",
    "cl rugi sl rugi semua rugi",
    "cl rugi sl rugi",
    "semua rugi bgstt", "semua rugi bgs",
    "mau cutloss sayang mau hold",
    "mau cutloss sayang",
    "hanya pengecut yang", "pengecut yang melakukan cutloss",
    "cutloss itu pengecut",
    "cl hanya orang lemah", "hanya orang lemah",

    # ── Dana dingin / rasionalisasi rational-sounding ─────────────
    "dana dingin", "uang dingin",
    "dana dingin better di hold", "uang dingin hold",
    "nyimpen dana dingin", "nyimpen uang dingin",
    "stop main saham", "anggap stop main",

    # ── Tetap hold meski hopeless ─────────────────────────────────
    "ga sanggup hold lagi", "udah ga sanggup hold",
    "kalo cl bisa rugi banyak", "kalau cl bisa rugi",
    "hold sampai kiamat", "hold kiamat",
    "masih hold sampai kiamat",
    "ga bisa cl", "tidak bisa cl",
    "sementara ga cl dulu",
    "ga cl dulu kecuali", "tidak cl dulu",
    "bertahun-tahun minus", "bertahun tahun minus",
    "race to the bottom", "nambah muatan biar", 
    "kalau makin ditambah", "makin ditambah jadi",
    "rugi itu belum ada", "rugi itu belum",
    "jangan pernah salahkan",                 # rasionalisasi rugi
    "adro kena sl", "kena sl tapi",
    "pasar saham naik besok",                 # prediksi optimis = LA denial
    "ada pepatah",                            # "ada pepatah sell in may" = bias hold
    "akhir tahun balik", "balik lagi akhir",

    # ── Ovt / overthinking ────────────────────────────────────────
    "ga ovt", "gak ovt", "ga overthinkin",
    "ga overthinking", "tidak ovt",

    # ── Implicit LA — frasa tanpa kata kunci eksplisit ────────────
    "abis modal tapi masih harap",
    "abis modal tapi aku",
    "nyangkut di emiten berdividen",
    "berdividen gedhe mah aman",
    "tetep ada uang tunggu",
    "jgn ovt gw dulu hold",
    "hold admr naik turun akhirnya",
    "tenang aja guys jgn ovt gw dulu hold",
    "berdoa utk sahabat yang udah masuk",
    "sahabat yang udah masuk tetap kuat",
    "kalo sampe lebaran ga minus",
    "sampai lebaran haji tidak minus",
    "dari profit 30% sekarang jadi",
    "masih hold harga ipo",
    "sisa lot ngikut aja",
    "klo mau hold jgn",                 # [455] implicit hold warning = LA
    "yang ngga pernah ditawarkan",      # [499] porto implicit LA
    "masih memantau menunggu kepastian rups",  # [812]
    "wait n see saya sih typical",
    "teknikal analisa akan kalah jika ihsg dalam keadaan crash",  # [934]
    "saran yg lagi floating loss mending diam",
    "saran yang lagi floating loss mending",
    "kuncinya bisa sabar atau tidak menunggu recovery",  # [1036]
    "pasti hampir 98% saham ihsg yang bagi dividen pasti turun",
    "loss 30jtan di kripto sisa dana main di saham",  # [908]

    # ── Implicit LA batch baru ────────────────────────────────────
    "tidak berlaku bagi adro ovt",
    "masih memantau menunggu kepastian rups",
    "loss 30jtan di kripto sisa dana main di saham",
    "setiap akhir sesi 2 di guyur float loss",
    "teknikal analisa akan kalah jika ihsg dalam keadaan crash",
    "kuncinya bisa sabar atau tidak menunggu recovery",
    "dari yang paling yakin menjadi ragu dan bimbang",
    "menjadi ragu dan bimbang",
    "terlalu banyak asing posisinya floating loss",
    "dari ath udah turun 55%", "ath udah turun 55",
    "masih aman lah balik ke harga awal beli",
    "saran yang lagi floating loss",
    "analisa teknikal gaakan berguna kalau ihsg crash",
    "punya di harga ipo mungkin masih santai dibawa arb",
    "hold avg 230 up masih bisa makan kan",
    "holder avg", "holder avg 230",
    "masih bisa makan kan",
]

# --- LOSS_AVERSION_AVERAGING ---
# Beli lagi saat harga turun untuk menurunkan HPP.
# CATATAN: pakai "lagi dca" / "mau dca" bukan "dca" saja — terlalu umum.
LOSS_AVERSION_AVERAGING = [

    # Averaging down
    "average down", "averaging down", "avg down",
    "biar rata", "beli lagi biar rata","makin anjlok makin", "makin turun makin",  # dividen yield rationalisasi
    "dividen yield", "yield makin jumbo",
    "sl sebagian tapi buy", "stop loss tapi beli",

    # DCA — hanya konteks aktif (bukan pertanyaan edukatif)
    "lagi dca", "dca terus", "mau dca", "dca", "breakeven price",
    "biar breakeven", "add posisi",
    "nambah posisi", "hpp makin turun",
    "turunin hpp", "harga pokok",
    "dollar cost averaging", "cicil beli", "cicilan beli",
    
    # Akumulasi
    "serok", "nyerok", "serok lagi",
    "tambah lot", "nambah lot", "tambah posisi saat turun", 
    "nambah posisi saat merah",
    "biar breakeven", "breakeven cepet",
    "kesempatan averaging",

    # Beli karena murah
    "harga murah sekarang", "kesempatan beli",
    "murah nih", "lagi murah", "diskon nih", "diskon gede",
    "turunkan cost", "lower cost basis",

    # English
    "buy more when down", "add more", "buy more",
    "accumulate", "buying opportunity", "cheap now",
    "lower my cost", "cost basis",

    # ── Slang Stockbit / Telegram ──────────────────────────────────────
    # "haka" removed — handled by bias_detector adj AAAAAA (FOMO)
    "avgd", "avg down",          # abbreviated slang
    "avg bulat", "supaya avg",   # "supaya avg bulat ke 3800"
    "beli di bawah avg",
    "kapan lagi harga murah", "kapan lagi beli murah",
    "kapan lagi bisa beli big",  # "kapan lagi bisa beli big banks harga murah"
    "belanja di",                # "belanja di 7100-7200-7300" = averaging in
    "cicil beli lagi",
]

# --- LOSS_AVERSION_BLAME ---
# Menyalahkan bandar / manipulasi untuk menghindari mengakui analisis salah.
LOSS_AVERSION_BLAME = [

    # ── Blame patterns batch baru ─────────────────────────────────
    "bandar cabut pasang bid",
    "lebih parah dari dada",
    "dilihat dari harga 1500",
    "harga sekarang 320 murah banget",
    "harga sekarang murah banget ya hehe",

    # Tuduhan bandar
    "salah bandar", "bandar jahat", "digoreng bandar",
    "digoreng", "manipulasi", "dimanipulasi",
    "pasti ada bandar", "bandar main",

    # Big player / institutional selling
    "ada yang jual gede", "ada yang jual besar", "big player jual",
    "suppressed harga", "nyuppress",

    # Harga tidak wajar
    "tidak wajar turun", "ga wajar turun",
    "harusnya udah naik", "harusnya naik",
    "bukan fundamental", "bukan salah fundamental",

    # English
    "market manipulation", "being manipulated",
    "someone is selling", "someone dumped", "big player",
    "suppressing", "not natural", "shouldn't be down",
]


# =============================================================================
# BAGIAN 3 — CONFIRMATION BIAS
# Sinyal: user mencari validasi, echo chamber, atau menyaring info negatif
# =============================================================================

# --- CONFIRMATION_LEADING ---
# Pertanyaan yang sudah mengandung jawaban yang diinginkan.
# Contoh: "BBCA bagus kan?" = user sudah tau jawabannya, minta konfirmasi.
CONFIRMATION_LEADING = [

    # Pertanyaan validasi eksplisit
    "bener kan", "benar kan", "bener ga?", "gue bener ga?", "bener kan ya?",
    "iya ga?", "bagus kan", "bagus ga", "oke kan",
    "setuju ga", "sependapat ga", "sepakat ga",
    "besar banget kan", "undervalued kan", "keputusan gue bener", "analisis gue bener"
    "solid kan", "bagus banget kan",
    "potensinya besar kan", "konfirmasi dong", "konfirmasi nih",
    "konfirmasi dulu", "tolong konfirm", "tolong konfirmasi", "konfirmasi keputusan",
    "confirm dong", "gue yakin", "gue udah yakin",
    "gue bener ga", "gue bener kan", "yakin nih",

    # ── "Ya kan?" pattern — minta konfirmasi ────────────────────
    "ya kan?", "ya kan",
    "masih bisa kan", "bisa kan?",
    "pasti bisa ya kan", "tetap kuat ya kan",
    "bakalan naik ya kan", "bakalan naik kan",
    "multi-bagger ya kan", "the next multi-bagger",
    "masih bisa naik kan", "naik kan?",

    # ── Confirmation Seeking ────────────────────
    "kann bener", "bener kann", "iyakan", "iyakan?", "kan bener",
    "yakinkan aku", "tuh kann", "bener bener memang",

    # ── Appeal to authority — CB by association ──────────────────
    "konglo pegang", "konglomerat pegang",
    "bandarnya yang aman", "ada bandarnya",
    "punya prabowo", "punya jokowi", "punya konglomerat",
    "punya presiden", "milik konglomerat",
    "saham punya adek", "saham punya anak",
    "dapat kabar dari veteran", "kata veteran",
    "disuru masuk", "disuruh masuk",
    "bisa yakinin", "gw bisa yakinin",
    "yang butuh conviction",

    # ── Pilihan sudah dibuat, cari validasi ──────────────────────
    "udah bener masuk", "bener masuk kan",
    "ini pilihan tepat",
    "gua milih masuk X soalnya",

    # Minta alasan untuk keputusan yang sudah ada
    "alasan beli", "alasan mendukung", "minta alasan mendukung",
    "alasan masuk", "alasan tambah", "kasih alasan beli",
    "kasih alasan", "kenapa harus beli", "kenapa bagus",
    "kenapa pilihan terbaik", "jelasin kenapa bagus",
    "jelasin kenapa masuk", "jelasin dong",
    "dukung keputusan", "rekomendasiin",

    # Sudah hampir memutuskan — minta dorongan terakhir
    "gue udah mau masuk", "udah mau beli", "udah mau entry",
    "gue yakin banget", "udah yakin mau",
    "worth it ga nih", "worth it ga ya", "worth ga nih",
    "layak beli", "worth it beli",
    "potensi bagus kan", "potensi besar kan",
    "prospek bagus kan", "prospek oke kan",
    "validasi", "validate", "convince me",

    # English
    "give me reasons", "reasons to buy", "reasons why buy",
    "solid right?", "looks solid right?",
    "good right?", "looks good right?",
    "great prospects", "good prospects", "great potential",
    "should i buy", "worth buying", "confirm", "agree?",
    # ── Post-entry seeking validation ────────────────────────────
    "udah bener masuk", "bener masuk kan",
    "gua milih masuk X soalnya", "gua milih masuk",
    "pilihan tepat",
    "biar suhu yang ono", "biar suhu bisa",   # referensi ke expert/mentor


]

# --- CONFIRMATION_ECHO ---
# User mengutip "semua orang bilang" sebagai pembenaran opini sendiri.
# Beda dengan FOMO_SOCIAL: ini soal memvalidasi pendapat, bukan takut ketinggalan.
CONFIRMATION_ECHO = [

    # Konsensus / mayoritas sebagai otoritas
    "semua bilang", "semua analis bilang", "semua di grup",
    "rata-rata bilang", "rata-rata analisis",
    "semua positif", "analisisnya semua positif",
    "semua yang gue baca positif", "semua bacaan gue", "konsensus", 
    "semua setuju", "semua sepakat",
    "semua tanda", "semua bilang mau naik", "semua analis setuju",
    "semua percaya", "gue percaya mereka", "kata semua analis",

    # Influencer / komunitas sebagai pembenaran
    "semua influencer", "semua yang gue follow",
    "analis bilang", "prediksi analis",
    "kata komunitas", "kata grup",

    # English
    "everyone says", "everyone agrees", "all analysts",
    "consensus is", "community says", "group says",
    "analysts say", "all the analysts",
    "influencers say", "everyone i follow",
    # ── Memantapkan diri melalui orang lain ──────────────────────
    "memantapkan diri buat cl", "memantapkan diri",
    "cutloss apa hari ini kawan", "cutloss apa hari ini",
    "kalau belom cl blm rugi", "kalau belum cl belum rugi",
    "belum cl belum rugi",
    "ovt bareng", "ovt sendirian", "ga mau ovt sendirian",
    "porto tmn2 gimana", "porto teman gimana",
    "cari teman yang sama rugi", "cari teman senasib",

    # ── Memantapkan diri melalui orang lain ──────────────────────
    "memantapkan diri buat cl", "memantapkan diri",
    "cutloss apa hari ini kawan", "cutloss apa hari ini",
    "kalau belom cl blm rugi", "kalau belum cl belum rugi",
    "belum cl belum rugi",
    "ovt bareng", "ovt sendirian", "ga mau ovt sendirian",
    "porto tmn2 gimana", "porto teman gimana",
    "cari teman yang sama rugi", "cari teman senasib",

    # ── Validasi melalui daftar institusi ─────────────────────────
    "msci - ", "goldman sachs -", "moody's -",

    # ── Daftar otoritas eksternal (validasi melalui institusi) ────
    "msci - ", "goldman sachs -", "moody's -",          # daftar downgrade = CB mencari pola
]
# User secara eksplisit minta analisis yang mendukung saja, bukan balanced.
CONFIRMATION_POSITIVE = [
    "yang positif aja", "positif aja ya", "minta yang positif",
    "analisis positif", "analisis mendukung", "yang mendukung",
    "minta analisis yang mendukung", "analisis yang positif aja",
    "yang bagus aja", "alasan positif", "dukung aja",
]

# --- CONFIRMATION_OVERCONFIDENT ---
# CB halus — tidak ada leading question eksplisit tapi ada pola kognitif:
#   (a) Overconfidence: "analisis gue pasti benar"
#   (b) Dismiss negatif: "yang bilang jelek ga paham"
#   (c) Selective seeking: "cari berita positif buat yakinkan diri"
#   (d) Anchoring harga beli: "harga wajarnya minimal di harga beli gue"
#   (e) Post-purchase rationalization: "abis beli, cari analisis bullish"
CONFIRMATION_OVERCONFIDENT = [

    # (a) Overconfidence
    "pasti naik", "pasti bagus", "pasti rebound", "pasti recovery",
    "pasti benar", "pasti bener", "yakin banget", "gue yakin ini",
    "analisis gue benar", "analisis gue tepat", "riset gue sudah",
    "menurutku pasti", "menurut analisis gue",
    "ga paham", "pasti ga paham", "ga ngerti", "yang kontra ga paham",
    "pilihan gue bener", "emang bener", "saham terbaik",
    "tesis gue masih valid", "masih valid", "tesis gue valid",
    "sesuai prediksi gue", "sesuai persis prediksi", "sesuai analisis gue",
    "second opinion", "ga perlu second opinion",
    "berdasarkan analisis gue", "analisis gue bilang",
    "masuk berdasarkan analisis", "bukan karena orang lain", "bukan ikut-ikutan",
    "hidden gem", "market belum sadar", "tunggu market sadar",
    "undervalued banget", "market belum tau",

    # Prediksi self-serving
    "aku prediksi harga bisa naik", "maklum saya punya sahamnya",
    "saya semakin yakin", "menurut analisa saya pribadi",
    "setiap jam 11-12 harga pasti",

    # Hindsight/validasi prediksi
    "nah kan dibilang juga apa", "kann pada jual abis itu naik",
    "masih bisa masuk nih sebelum ara",
    "mau gua kasih tau kenapa ni saham",

    # Selective bullish framing
    "bbca bukan suram ya guys",
    "mantap kali gerakannya sdh bisa menolak arb",
    "jangan denial iya ini belum berhenti",

    # Bandarmologi / akum selective
    "barang beredar sedikit mayoritas dipegang emiten",
    "di-backing konglo china", "backed konglo china cngr",
    "akumulasi tetap dijaga institusi",
    "asing sudah akum bottom area sudah lewat",
    "kepala nya jualan terus karna tau ada utang",

    # Selective expectation
    "harusnya senin naik ngga sih kalo dari chart",
    "harusnya titik support", "harusnya support h-3 lebaran",
    "harusnya bei kasih batas bisnis owner",
    "senin kayak nya ga koreksi malah bakal lanjut up",
    "ada yg sependapat",

    # Recovery CB framing
    "fase bullish recovery sudah tembus saatnya ke resistance",

    # (b) Dismiss informasi negatif
    "cuma sementara", "sementara aja", "itu bukan masalah besar",
    "itu overhyped", "ga perlu khawatir soal itu",
    "yang bilang jelek", "yang kontra pasti", "yang bilang salah pasti",
    "mereka ga paham", "ga ngerti bisnis", "ga ngerti fundamental",
    "faktor eksternal", "bukan masalah fundamental",
    "gue ga setuju", "gue tidak setuju",
    "faktor eksternal",
    "bukan masalah fundamental", "bukan isu fundamental",
    "itu salah", "bilang salah", "yang bilang salah",
    "bukan bias", "ini conviction", "ini bukan fomo",
    "setuju sama analisis gue", "setuju dengan analisis gue",
    "yang kontra biasanya", "yang kontra selalu",
    "yang lain salah", "orang lain salah",
    "salah pasar", "pasar salah", "market salah",
    "tidak mencerminkan value", "tidak mencerminkan",
    "gue filter", "gue saring", "disaring",
    "saham sultan",

    # (c) Selective information seeking
    "cari berita positif", "cari-cari berita bagus", "nyari yang positif",
    "buat yakinkan diri", "buat tenangkan diri", "biar lebih yakin",
    "konfirmasi keyakinan", "konfirmasi tesis",

    # Multi bagger CB patterns
    "multi bagger", "multi-multi bagger", "multi bagger saham",
    "real case multi bagger", "sudah biasa multi bagger",

    # Terbukti CB patterns  
    "terbukti omongan saya", "terbukti selalu cepet pulih",
    "terbukti fundamental kuat", "udah terbukti",
    "pasti kali ini juga",  # CB extrapolation

    # Prediksi CB patterns
    "prediksi yang bener tentang ini saham",
    "sejauh ini on track sesuai yang saya posting",
    "menurut analisa saya pribadi",
    "menurut keyakinan saya",
    "saya semakin yakin",

    # Bandarmologi / akum CB
    "layangkan pandangan tajam", "fenomena lonjakan anomali",
    "akan dijaga dan ada yang akum besar",
    "barang beredar sedikit mayoritas di pegang",
    "akumulasi tetap dijaga institusi",

    # Recovery CB framing
    "fase bullish recovery sudah tembus",
    "asing sudah akum bottom area sudah lewat",
    "dari pengalaman gue di",  # CB bandar pattern
    "kepala nya jualan terus karna tau",  # CB conspiracy

    # (d) Anchoring pada harga beli sendiri
    "harga wajarnya", "harga seharusnya", "harusnya di atas",
    "di bawah valuasi gue", "valuasi gue bilang",
    "harga beli gue", "di harga beli gue",

    # (e) Post-purchase rationalization
    "abis beli", "setelah masuk", "udah masuk tadi",
    "udah beli tadi", "terlanjur masuk",

    # ── "Told you so" / vindikasi — CB klasik ────────────────────────
    # User menunggu/menikmati momen di mana analisisnya terbukti benar
    "told you so", "kata gue", "gue udah bilang", "gue bilang dari dulu",
    "gue bilang", "sudah gue bilang", "kan gue bilang",
    "terbukti kan", "terbukti benar", "terbukti", "akhirnya terbukti",
    "ditunggu told you so", "nunggu told you so",
    "vindicated", "gue benar ternyata",
    "kata gue dari awal", "sehat sehat dah kata gue",

    # Dismiss orang lain yang salah = CB selective
    "pamer beli", "yang beli di atas", "yang beli mahal",
    "makanya jangan", "pantesan", "pantas saja",
    "banyak yang tebar fear", "tebar fear", "yang sebar fear",
    "tebar ketakutan", "sebar ketakutan",

    # Post-entry rationalization (sudah masuk, sekarang cari konfirmasi)
    "sudah masuk hari ini", "sudah beli hari ini",
    "tinggal nunggu rebound", "nunggu rebound ke",
    "optimis ke", "optimis bakal",
    "yakin apa yang dibeli", "yakin sama pilihan",

    # Analisis teknikal sebagai selektif konfirmasi (hanya jika sudah ada sinyal CB lain)
    # CATATAN: "confirm break", "catatan pribadi", "update ihsg" dipindah ke
    # ANALYTICAL_PATTERNS agar tidak false-positive untuk kalimat teknikal murni

    # ── Prediksi self-serving (batch baru) ───────────────────────
    "aku prediksi harga bisa naik", "maklum saya punya sahamnya",
    "saya semakin yakin", "menurut analisa saya pribadi",
    "setiap jam 11-12 harga pasti",
    "ada yg sependapat",

    # ── Hindsight / validasi prediksi ────────────────────────────
    "nah kan dibilang juga apa", "kann pada jual abis itu naik",
    "masih bisa masuk nih sebelum ara",
    "mau gua kasih tau kenapa ni saham",
    "sejauh ini on track sesuai yang saya posting",

    # ── CB disconfirmation ────────────────────────────────────────
    "bbca bukan suram ya guys",
    "mantap kali gerakannya sdh bisa menolak arb",
    "jangan denial iya ini belum berhenti",
    "gak perlu denial masa saham konglo",
    "cuma koreksi tipis tapi damagenya kena banget ke",

    # ── Bandarmologi / akum selective ────────────────────────────
    "barang beredar sedikit mayoritas dipegang emiten",
    "di-backing konglo china", "backed konglo china cngr",
    "akumulasi tetap dijaga institusi",
    "asing sudah akum bottom area sudah lewat",
    "kepala nya jualan terus karna tau ada utang",
    "layangkan pandangan tajam", "lonjakan anomali",
    "akan dijaga dan ada yang akum besar",

    # ── Selective expectation harusnya ───────────────────────────
    "harusnya senin naik ngga sih kalo dari chart",
    "harusnya titik support", "harusnya support h-3",
    "harusnya bei kasih batas bisnis owner",
    "senin kayak nya ga koreksi malah bakal lanjut up",
    "bisakan harusnya naik",

    # ── Recovery CB framing ───────────────────────────────────────
    "fase bullish recovery sudah tembus saatnya ke resistance",
    "bottom area sudah lewat saatnya menuju recovery bertahap",
    "dari pengalaman gue di",
    "bukan kaum fomo beli di harga",
    "ritel yang fomo ga belajar dari case",

    # ── CB conf terlalu rendah — boost dengan lebih banyak exact match ───
    "harusnya adalah titik support",    # [808]
    "titik support ihsg yg sebenarnya",
    "harusnya adalah titik",
    "gak mau turun lagi nih udah bottom",  # [821]
    "udah bottom ke kan masih bisa",
    "keajaiban si saham fundamental",   # [845]
    "apa nih aneh bener pergerakannya gocap",
    "lagi banyak yg bahas freefloat",   # [867]
    "pani aman jaya free float",
    "besok arb berjilid buruan pasang sell",  # [979]
    "lapkeu jelak mana ya yang semalem",
    "fase bullish recovery", "recovery sudah tembus saatnya",  # [1024]
    "bottom area sudah lewat di",       # [1025]
    "menuju recovery bertahap",
    "dipastikan harusnya backdoor is real",  # [801]
    "ratio nya 90:253",
]


# =============================================================================
# BAGIAN 4 — NETRAL / OVERRIDE
# Dipakai untuk mendeteksi kalimat yang seharusnya NONE:
# pertanyaan edukatif, analitis objektif, atau pertanyaan risiko.
# =============================================================================

# --- RISK_KEYWORDS ---
# Pertanyaan risiko / downside = sinyal kuat pertanyaan objektif → NONE.
RISK_KEYWORDS = [
    "risiko", "risk", "downside", "bahaya", "kenapa turun",
    "alasan jual", "red flag", "masalah", "hutang", "debt",
    "overvalued", "terlalu mahal",
    "skenario buruk", "skenario terburuk", "worst case",
    "invalidate", "thesis salah", "apa yang salah",
    "seberapa jauh turun", "how far can it fall",
    "cutloss kalau", "cut loss kalau",
]

# --- ANALYSIS_KEYWORDS ---
# Kata kunci analisis fundamental / valuasi = pertanyaan objektif → NONE.
ANALYSIS_KEYWORDS = [
    "fundamental", "revenue", "earnings", "laporan keuangan",
    "valuasi", "pe ratio", "p/e", "pb ratio",
    "roe", "roa", "dividen", "dividend",
    "cash flow", "neraca", "laba", "pendapatan",
    "balance sheet", "income statement", "debt",
]

# --- EDUCATION_PATTERNS ---
# Pola pertanyaan edukasi — "apa itu X", "bagaimana cara Y", "A vs B".
# Match → override ke NONE kecuali ada sinyal bias yang kuat.
EDUCATION_PATTERNS = [

    # Definisi / penjelasan konsep
    "apa itu ", "apa yang dimaksud", "definisi ",
    "jelaskan ", "tolong jelaskan",
    "apa itu confirmation bias", "apa itu loss aversion",
    "apa bedanya fomo", "bedanya fomo", "definisi fomo",
    "apa pendapat analis", "pendapat analis konsensus",
    "konsensus analis", "target harga konsensus",

    # Tutorial / cara melakukan sesuatu
    "bagaimana cara ", "cara menghitung", "cara membaca",
    "how to ",

    # Perbandingan / perbedaan
    "bedain ", "bedakan ", "perbedaan antara",
    " vs ", " versus ",
    "what is ", "what are ", "explain ", "difference between",

    # Cut loss / strategi — pertanyaan strategi, bukan sedang nyangkut
    "kapan harus cut loss", "kapan cutloss", "kapan jual",

    # Indikator teknikal
    "indikator apa", "indikator terbaik", "apa indikator",
    "apa yang terbaik untuk",

    # Dampak makro / kebijakan
    "dampak kenaikan suku bunga", "dampak suku bunga",
    "bagaimana dampak",
]

# --- ANALYTICAL_PATTERNS ---
# Pola pertanyaan analitis / historis.
# Match → override ke NONE kecuali ada sinyal bias yang kuat.
ANALYTICAL_PATTERNS = [

    # ── Observer / warning NONE patterns (batch baru) ────────────
    "disuruh ngekos",
    "tiba2 terpikir jadi pelajaran buat kita semua",  # [811] meta-analysis NONE
    "jadi pelajaran buat kita semua",
    "saham masih nyangkut tapi butuh uang buat lebaran",  # [822]
    "tapi butuh uang buat lebaran",
    "warren buffet masuk ihsg pun pasti banyak cl",  # [954] humor/sarkasme
    "pasti banyak yg jual karena kemaren diajak uji mental",  # [1035]
    "diajak uji mental turun tajem dan sekarang recovery",
    "disuruh cuci piring sama bandar",
    "hiburan bagi saya adalah melihat banyak nya",
    "ngeri2 baca isi stream",
    "bakal ara g ntar", "bakal ara ga ntar",
    "bagaimana performa", "performa saat", "bagaimana saat",
    "siapa yang jual", "siapa yang beli",
    "seberapa jauh", "how far", "how much",
    "historically", "secara historis",
    "sarannya dong", "perkiraan bakal kemana",
    "ga bisa ke buy", "masih di tahan bandar", "ora nyerok",
    "apa yang bisa", "apa yang membuktikan",
    "what would invalidate", "what could go wrong",
    "during market", "saat ihsg", "saat market",
    "selama ihsg koreksi", "kapan ara", "kapan aranya", "masih ara",
    "masi ara",
    "update info", "potensi berapa",
    "untuk catatan pribadi", "catatan pribadi",
    "update ihsg", "update porto", "update posisi",
    "short term", "short-term", "medium term",
    "masih spekulasi", "masih belum pasti", "belum ada kepastian",
    "jebakan betmen",

    # Override FP NONE→LA: pertanyaan sosial / minta saran
    "guys minta saran", "minta saran dong", "minta pendapat",
    "tolong sarannya dong", "sarannya dong",
    "guys tolong", "kalian gimana", "kalian tim",
    "tim cl atau", "tim hold atau", "tim serok atau",
    "wait n see", "wait and see",
    "pada gimana", "pada bingung",
    "pada panic selling kah", "masih pada panic",
    "mending cut loss apa enggak", "mending cl apa",
    "cl atau serok", "serok atau cl",
    "cara ngitung", "cara hitung", "cara menghitung",
    "ngitung time to", "hitung time to",

    # ── Override FP FOMO: pertanyaan informasi IPO/listing ───────
    "kapan goto akan ipo", "kapan ipo di bursa",
    "akan ipo di bursa lain", "ipo di bursa lain",
    "kapan listing di", "rencana listing",

    # ── Override FP FOMO: observasi market drop ──────────────────
    "sekalinya turun gak kirakira", "sekalinya turun",
    "dampak ke setiap emiten",
    "ihsg soon wd", "soon wd", "last day in 2025",
    "last day in 2026",

    # ── Override FP LA: pertanyaan prediksi saham ────────────────
    "perkiraan bakal kemana", "besok perkiraan bakal",
    "sarannya dong ini saham besok",

    # ── Override FP LA: curhat setelah CL (sudah aksi) ───────────
    "gw udh cl", "gue udah cl",
    "udh cl 2 jt", "abis cl tadi",
    "pagi pagi cl", "cl pagi pagi",

    # ── Override FP FOMO: pertanyaan teknikal support ─────────────
    "udah di support belum", "di support belum",
    "bakal mantul besok", "mantul besok",

    # Override FP NONE→CB: komentar tentang orang lain yang bias
    "ketika ritel unyu", "ritel unyu sok",
    "sokaan menganalisa", "sok-an menganalisa",
    "dengan bhsa basi", "apa gue bilang",
    "kasian amat ritel", "kasian ritel",
    "jangan pernah salahkan siapa pun",
    "rugi itu belum ada",
    "membasuh luka", "membasuh luka ihsg",
    "sekarang jadi terbiasa", "jadi terbiasa",
    "katanya klo lagi perang", "katanya kalau perang",
    "gue bilang apa bandarnya",
    "gue bilang apa saham ini gajelas",
    "gua balik modal aja",
    "dah gue bilang turun",
    "gue bilang apa, aman aja",
    "pantesan membernya pada rugi",
    "lagi buang barang pantesan turun",
    "q4 laba bersihnya naik to pantesan",
    "Hahaha gue bilang juga apa",
    "udah gue bilang dri tgl",
    "ora nyerok",                            # Jawa: tidak beli = tidak ada bias

    

]