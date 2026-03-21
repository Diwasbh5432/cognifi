# rag.py — CogniFi RAG Engine
# Knowledge base dibangun dari 10 dokumen riset project CogniFi.
# Setiap chunk = pengetahuan domain spesifik yang diinjeksikan ke LLM prompt.
#
# Usage:
#   from rag import retrieve_context_formatted
#   context = retrieve_context_formatted(
#       query="semua orang beli, takut ketinggalan",
#       bias_type="FOMO", top_k=3
#   )

import os
import chromadb
from chromadb.utils import embedding_functions

DB_PATH     = os.path.join(os.path.dirname(__file__), ".chromadb")
COLLECTION  = "cognifi_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"

CORPUS = [
    # ═══ FOMO ═══════════════════════════════════════════════════════════════
    {
        "id": "fomo_definisi_bahaya", "bias": "FOMO", "category": "teori",
        "text": (
            "FOMO (Fear of Missing Out) adalah ketakutan kehilangan peluang yang sedang "
            "dialami orang lain, yang mendorong keputusan investasi tanpa analisis memadai. "
            "FOMO bukan hanya bias tersendiri melainkan amplifier — ia memperkuat bias lain "
            "seperti loss aversion dan herd behavior. Ini membuatnya paling berbahaya di "
            "jangka pendek: investor masuk bukan karena thesis tapi karena takut menjadi "
            "satu-satunya yang ketinggalan. Nguyen et al. (2025) dalam studi terhadap 727 "
            "investor mengkonfirmasi loss aversion dan herd behavior positif mempengaruhi FOMO."
        )
    },
    {
        "id": "fomo_sinyal_deteksi", "bias": "FOMO", "category": "deteksi",
        "text": (
            "Sinyal FOMO yang bisa dideteksi sistem: "
            "(1) Kata kunci urgensi: 'mau naik', 'bakal pump', 'buruan', 'masih sempet', "
            "'kayaknya mau', 'semua orang pada beli', 'rame banget'. "
            "(2) Kata kunci social proof: 'temen gua', 'kata influencer', 'di grup', "
            "'pada profit', 'semua hijau', 'viral', 'trending', 'rame di tiktok'. "
            "(3) Absensi kata analisis: tidak ada 'fundamental', 'revenue', 'earnings', "
            "'laporan keuangan', 'valuasi', 'PE ratio', 'debt', 'cash flow'. "
            "(4) Sinyal harga: kenaikan >15-20% dalam 5 hari, volume 2x+ rata-rata. "
            "FOMO terdeteksi saat user bereaksi terhadap momentum harga, bukan fundamental."
        )
    },
    {
        "id": "fomo_scoring_logic", "bias": "FOMO", "category": "deteksi",
        "text": (
            "Scoring FOMO: text signals bobot 40%, price signals bobot 60%. "
            "Text: urgency >= 2 kata (+0.20), social proof >= 1 (+0.15), analysis absent (+0.05). "
            "Price: kenaikan >20% dalam 5 hari (+0.30), >15% (+0.20); "
            "volume ratio >2.0x (+0.20), >1.5x (+0.10). Score max 1.0. "
            "Threshold intervensi: 0.40. Di bawah threshold tidak ada intervensi. "
            "Sistem tidak mengklaim 'kamu pasti FOMO' tapi 'pola ini 87% mirip FOMO historis'."
        )
    },
    {
        "id": "fomo_konteks_indonesia", "bias": "FOMO", "category": "konteks",
        "text": (
            "Konteks FOMO di Indonesia: kasus Timothy Ronald dan komunitas kripto — "
            "investor masuk tanpa memahami aset yang dibeli, semata karena tidak mau "
            "ketinggalan momentum di media sosial. Kasus serupa: hype Moodeng, IPO saham "
            "dengan antrian panjang karena semua orang beli, bukan karena fundamental. "
            "84% investor kripto membuat keputusan karena FOMO, bukan analisis fundamental. "
            "Posisi yang dibuka saat social media attention tertinggi menghasilkan return "
            "rata-rata -8.5%, sementara rata-rata return keseluruhan positif."
        )
    },
    {
        "id": "fomo_counter_evidence_format", "bias": "FOMO", "category": "intervensi",
        "text": (
            "Format counter-evidence FOMO yang benar: "
            "Tampilkan kondisi saat ini (misal: '[Ticker] naik 28% dalam 5 hari, volume 2.3x'), "
            "lalu data historis episode serupa: 'Data historis GOTO.JK 2022-2026: "
            "6 kejadian serupa, 5 dari 6 diikuti koreksi dalam 30 hari, "
            "rata-rata koreksi 31%, probabilitas historis 83%'. "
            "Lalu satu pertanyaan reflektif: "
            "'Apakah ada perubahan fundamental di [Ticker] yang mendukung kenaikan ini, "
            "atau kamu bereaksi terhadap pergerakan harga?' "
            "Sistem tidak merekomendasikan beli atau jual. Hanya data dan satu pertanyaan."
        )
    },
    {
        "id": "fomo_system1_trigger", "bias": "FOMO", "category": "teori",
        "text": (
            "Kahneman (2011): System 1 (cepat, emosional) selalu beroperasi lebih dulu. "
            "System 2 (analitis) datang kemudian, seringkali bukan untuk mengoreksi "
            "tapi untuk merasionalisasi keputusan yang sudah dibuat System 1. "
            "Trigger FOMO (konten TikTok, pesan WhatsApp grup, notifikasi broker) "
            "mengaktifkan System 1. Investor membuka broker, melihat harga naik, "
            "panik ketinggalan — semua sebelum System 2 sempat aktif. "
            "Intervensi efektif harus menciptakan friction yang mengaktifkan System 2 "
            "sebelum eksekusi, bukan setelahnya."
        )
    },
    # ═══ LOSS AVERSION ═══════════════════════════════════════════════════════
    {
        "id": "loss_aversion_definisi", "bias": "LOSS_AVERSION", "category": "teori",
        "text": (
            "Loss aversion (Kahneman & Tversky, Prospect Theory 1979): rasa sakit dari "
            "kerugian terasa dua kali lebih kuat dibanding kesenangan dari keuntungan setara. "
            "Koefisien loss aversion: 2.0-2.5. Manifestasinya paradoksal: "
            "saat untung investor terlalu cepat jual (takut profit hilang); "
            "saat rugi investor tahan terlalu lama (menolak realize loss). "
            "Dua perilaku berlawanan, satu akar: menghindari rasa sakit. "
            "Ini adalah bias paling deep-rooted dan paling merusak jangka panjang. "
            "Loss aversion ditemukan pada 60% retail investor di pasar berkembang."
        )
    },
    {
        "id": "loss_aversion_sinyal", "bias": "LOSS_AVERSION", "category": "deteksi",
        "text": (
            "Sinyal Loss Aversion yang bisa dideteksi: "
            "(1) Kata kunci denial: 'nunggu balik modal', 'pasti balik', 'ini cuma koreksi', "
            "'sabar aja', 'long term', 'fundamental bagus kok', 'rugi kalau jual'. "
            "(2) Kata kunci averaging down: 'average down', 'tambah lagi', "
            "'beli lagi biar rata', 'harga murah nih', 'dollar cost averaging'. "
            "(3) Kata kunci blame eksternal: 'salah bandar', 'digoreng', 'manipulasi', "
            "'harusnya naik', 'tidak wajar turun'. "
            "(4) Sinyal harga: unrealized loss <-10% dengan MA20 < MA50 (downtrend). "
            "Deteksi kunci: perubahan narasi dari 'investasi jangka panjang' ke 'nunggu balik modal'."
        )
    },
    {
        "id": "loss_aversion_scoring", "bias": "LOSS_AVERSION", "category": "deteksi",
        "text": (
            "Scoring Loss Aversion: text signals bobot 50%, price signals bobot 50%. "
            "Text: denial >= 2 kata (+0.25), averaging >= 1 kata (+0.15), blame >= 1 (+0.10). "
            "Price: unrealized loss <-20% (+0.30), <-10% (+0.15); downtrend MA20<MA50 (+0.20). "
            "Proxy buy price jika tidak diketahui: harga 45 hari lalu. "
            "Downtrend = konfirmasi teknikal bahwa saham dalam tren turun, bukan koreksi sementara."
        )
    },
    {
        "id": "loss_aversion_counter_evidence", "bias": "LOSS_AVERSION", "category": "intervensi",
        "text": (
            "Counter-evidence Loss Aversion: tampilkan data downtrend historis. "
            "Data yang relevan: berapa episode downtrend serupa di masa lalu, "
            "berapa yang recovery dalam N hari, rata-rata hari recovery, "
            "berapa yang tidak recovery dalam window yang ditentukan. "
            "Pertanyaan reflektif: 'Apakah thesis investasi awalmu masih valid atau "
            "kamu menambah posisi karena tidak mau mengakui kerugian yang sudah terjadi?' "
            "Odean (1998): saham yang investor jual (winners) outperform saham yang mereka tahan "
            "(losers) sebesar 3.4 poin persentase setahun setelahnya. Menahan rugi adalah "
            "strategi yang secara statistik kalah."
        )
    },
    {
        "id": "loss_aversion_averaging_trap", "bias": "LOSS_AVERSION", "category": "intervensi",
        "text": (
            "Averaging down trap: membeli lebih banyak saat harga turun untuk menurunkan "
            "breakeven price adalah manifestasi loss aversion, bukan strategi DCA yang valid. "
            "DCA valid: membeli secara teratur ke aset yang fundamentalnya tetap kuat. "
            "Averaging down driven loss aversion: membeli karena tidak mau akui kerugian, "
            "bukan karena fundamental berubah positif. "
            "Pertanyaan kritis: apakah ada perubahan fundamental yang positif sejak pertama beli? "
            "Jika tidak ada, averaging down hanya memperbesar exposure ke aset yang sedang downtrend."
        )
    },
    {
        "id": "loss_aversion_konteks_indonesia", "bias": "LOSS_AVERSION", "category": "konteks",
        "text": (
            "Konteks Loss Aversion di komunitas investasi Indonesia: saat portofolio hijau, "
            "investor diam. Saat portofolio merah dan call seseorang terbukti salah, "
            "tiba-tiba ada tuntutan, tuduhan, dan keramaian di komunitas. "
            "Ini persis pola Prospect Theory: kerugian mengaktifkan respons emosional "
            "jauh lebih kuat dibanding keuntungan setara. "
            "Pola khas: mulai dengan 'investasi jangka panjang', berubah ke 'nunggu balik modal' "
            "saat harga turun. Perubahan narasi ini adalah sinyal loss aversion yang kuat."
        )
    },
    # ═══ CONFIRMATION BIAS ═══════════════════════════════════════════════════
    {
        "id": "confirmation_bias_definisi", "bias": "CONFIRMATION_BIAS", "category": "teori",
        "text": (
            "Confirmation bias: kecenderungan mencari, menafsirkan, dan mengingat informasi "
            "yang mengkonfirmasi keyakinan yang sudah ada, sambil mengabaikan informasi "
            "yang bertentangan. Ini adalah bias paling invisible dan paling sulit diintervensi "
            "karena beroperasi di level seleksi informasi, bukan di level keputusan. "
            "Investor tidak merasa sedang bias karena mereka merasa sedang melakukan riset. "
            "Perbedaannya: riset sesungguhnya mencari yang membuktikan salah. "
            "Confirmation bias mencari yang membuktikan benar."
        )
    },
    {
        "id": "confirmation_bias_sinyal", "bias": "CONFIRMATION_BIAS", "category": "deteksi",
        "text": (
            "Sinyal Confirmation Bias: "
            "(1) Query leading: 'benar kan', 'bagus kan', 'pasti naik', 'kenapa naik', "
            "'alasan naik', 'prospek bagus', 'potensi besar', 'kenapa harus beli'. "
            "(2) Absensi kata risiko: tidak ada 'risiko', 'downside', 'bahaya', "
            "'kenapa turun', 'red flag', 'masalah', 'hutang'. "
            "(3) Echo chamber: 'kata komunitas', 'semua bilang', 'konsensus', 'semua setuju'. "
            "Confirmation bias tidak butuh price signal — deteksinya murni dari pola teks. "
            "Scoring: leading >= 2 (+0.35), risk absent (+0.35), echo >= 1 (+0.30)."
        )
    },
    {
        "id": "confirmation_bias_counter_evidence", "bias": "CONFIRMATION_BIAS", "category": "intervensi",
        "text": (
            "Counter-evidence Confirmation Bias: sajikan pertanyaan dan data yang biasanya "
            "tidak dicari user. Pertanyaan yang harus dijawab sebelum eksekusi: "
            "(1) Apa risiko terbesar [Ticker] saat ini? "
            "(2) Siapa yang menjual [Ticker] dan mengapa? "
            "(3) Apa yang bisa membuktikan thesis ini salah? "
            "(4) Bagaimana performa [Ticker] saat IHSG turun 10-15%? "
            "Data fundamental yang perlu dicek: PE ratio, debt to equity, revenue growth, "
            "profit margins, insider selling, performa saat market koreksi. "
            "Pertanyaan reflektif: 'Apa yang bisa membuktikan keputusan ini salah dan sudah kamu cari belum?'"
        )
    },
    {
        "id": "confirmation_bias_echo_chamber", "bias": "CONFIRMATION_BIAS", "category": "konteks",
        "text": (
            "Echo chamber di Indonesia: kasus Manta dan komunitas Timothy Ronald — "
            "setelah FOMO masuk, investor aktif mencari konten yang mengkonfirmasi "
            "keputusan mereka sudah benar. Berita negatif diabaikan. "
            "Kritik dianggap FUD (Fear, Uncertainty, Doubt). "
            "Komunitas echo chamber memperkuat keyakinan tanpa koreksi. "
            "Algoritma TikTok/YouTube memperkuat ini: setelah user nonton konten bullish, "
            "sistem sajikan lebih banyak konten bullish. "
            "'Riset' malam hari Reza sebenarnya bukan riset — ia mencari konten yang mengkonfirmasi "
            "keputusan yang sudah setengah dibuat sejak pagi."
        )
    },
    {
        "id": "confirmation_bias_ai_problem", "bias": "CONFIRMATION_BIAS", "category": "konteks",
        "text": (
            "AI justru memperburuk confirmation bias: ketika user tanya AI 'gimana prospek GOTO?', "
            "AI memberikan analisis sesuai prompt yang sudah bias. Garbage in, confirmation out. "
            "Dikonfirmasi tiga sumber: ScienceDirect (2024) — herding behavior lebih kuat "
            "empat bulan pertama setelah peluncuran ChatGPT. Sidley Austin (2024) — AI trading "
            "systems konvergen ke strategi sama saat terekspos sinyal yang sama (monoculture). "
            "Harvard Business School: semua pengguna AI yang sama konverge ke 'the bot view'. "
            "AI yang dirancang untuk memberi jawaban terbaik justru menciptakan herding "
            "behavior yang difasilitasi teknologi."
        )
    },
    # ═══ GENERAL ═════════════════════════════════════════════════════════════
    {
        "id": "persona_reza_profil", "bias": "GENERAL", "category": "persona",
        "text": (
            "User utama CogniFi: Reza, 23 tahun. Baru lulus atau tahun akhir kuliah, "
            "tidak ada penghasilan tetap. Belajar investasi dari TikTok, Instagram, "
            "influencer, dan peer-to-peer. 65% Gen Z mendapat info investasi dari influencer "
            "dan konten sosmed (Rohman & Safiih, 2024). "
            "54.92% dari 14.8 juta investor Indonesia berusia di bawah 30 tahun (OJK 2024). "
            "Pola keputusan Reza: trigger dari konten sosmed, buka broker, cek harga sudah naik, "
            "search YouTube untuk konfirmasi bukan verifikasi, beli karena takut ketinggalan, "
            "harga koreksi, tahan tidak mau realize loss, cari konten 'ini cuma koreksi sementara'."
        )
    },
    {
        "id": "decision_journey_titik_intervensi", "bias": "GENERAL", "category": "proses",
        "text": (
            "5 tahap perjalanan keputusan investor: "
            "1. TRIGGER: terekspos konten (TikTok, WhatsApp grup, notifikasi broker). System 1 aktif. "
            "2. RESPONS EMOSIONAL: buka broker, lihat harga — FOMO menguat atau loss aversion aktif. "
            "3. FILTER = TITIK INTERVENSI: mencari informasi tapi bukan untuk menguji, untuk konfirmasi. "
            "Di tahap ini keputusan belum dieksekusi, System 2 masih bisa diaktifkan. "
            "4. KEPUTUSAN: klik beli — post-decision rationalization mulai aktif. "
            "5. AFTERMATH: harga naik (overconfidence meningkat) atau turun (cognitive dissonance). "
            "Tahap 3 adalah satu-satunya jendela intervensi yang masih terbuka."
        )
    },
    {
        "id": "prinsip_intervensi_friction", "bias": "GENERAL", "category": "prinsip",
        "text": (
            "Tiga prinsip intervensi CogniFi: "
            "(1) Data beats opinion: sistem tidak bilang 'jangan beli' atau 'beli sekarang'. "
            "Sistem hanya menunjukkan apa yang terjadi di masa lalu pada kondisi serupa. "
            "(2) Intervensi bukan blokir: sistem menciptakan jeda cukup untuk System 2 aktif. "
            "Friction efektif adalah memperlambat bukan memblokir. Memblokir melanggar otonomi "
            "user dan akan ditolak secara psikologis. "
            "(3) Transparent by design: setiap angka bisa di-trace ke sumbernya. "
            "Tidak ada black box. User selalu bisa lanjut setelah membaca data."
        )
    },
    {
        "id": "prinsip_satu_pertanyaan", "bias": "GENERAL", "category": "prinsip",
        "text": (
            "Output intervensi selalu diakhiri tepat satu pertanyaan reflektif, tidak lebih. "
            "Pertanyaan ini bukan untuk dijawab ke sistem tapi untuk dijawab user ke dirinya sendiri. "
            "Tone yang benar: 'Apakah ada perubahan fundamental yang mendukung kenaikan ini, "
            "atau kamu bereaksi terhadap pergerakan harga?' "
            "Tone yang salah: 'Kamu sedang FOMO dan ini berbahaya. Jangan beli sekarang.' "
            "Yang tidak boleh ada di output: kata 'jangan', 'salah', 'berbahaya', 'kamu harus', "
            "prediksi harga, opini tentang aset, lebih dari satu pertanyaan."
        )
    },
    {
        "id": "edukasi_tidak_cukup", "bias": "GENERAL", "category": "prinsip",
        "text": (
            "Edukasi tidak cukup untuk mengatasi bias kognitif. "
            "Kahneman sendiri mengakui: setelah puluhan tahun mempelajari cognitive bias, "
            "ia masih mengalaminya. Mengetahui bias tidak membuat imun terhadapnya. "
            "Informasi di pasar modal Indonesia tersedia lebih dari cukup. "
            "Yang tidak ada adalah mekanisme intervensi di momen keputusan. "
            "Solusinya bukan pengetahuan lebih — solusinya friction yang tepat di waktu yang tepat. "
            "Kahneman: System 2 butuh waktu dan ruang untuk aktif. Friction menciptakan ruang itu."
        )
    },
    {
        "id": "gap_behavioral_ai", "bias": "GENERAL", "category": "konteks",
        "text": (
            "Gap behavioral AI di finance (Anthropic Economic Index 2026): "
            "Financial analysts memiliki observed exposure 57.2% — masuk top 10 paling terekspos. "
            "Namun semua task yang ter-cover bersifat analitis (data, laporan, riset). "
            "Tidak ada satu pun task yang menyentuh layer behavioral: "
            "deteksi bias kognitif investor, intervensi sebelum keputusan impulsif, "
            "counter-evidence real-time. Gap ini bukan tentang kemampuan AI — "
            "AI capability sudah ada. Gap ini tentang di mana AI belum diarahkan. "
            "CogniFi mengisi layer behavioral yang 0% ter-cover."
        )
    },
    {
        "id": "biaya_bias_data", "bias": "GENERAL", "category": "data",
        "text": (
            "Data kuantitatif dampak bias kognitif investor: "
            "Behavioral bias menjelaskan 43.44-63.54% variasi return portofolio retail "
            "(Springer Nature, 2025). Lebih dari separuh performa portofolio ditentukan "
            "bukan oleh kualitas aset tapi oleh bias saat mengambil keputusan. "
            "Loss aversion ditemukan pada 60% retail investor di pasar berkembang. "
            "Herding bias: 50% retail investor, korelasi negatif dengan return (r=-0.48, p<0.03). "
            "Social media attention: posisi dibuka saat attention tertinggi return rata-rata -8.5%."
        )
    },
    {
        "id": "existing_solutions_gap", "bias": "GENERAL", "category": "konteks",
        "text": (
            "Landscape solusi yang ada dan gap-nya: "
            "Bloomberg/AlphaSense: cover informasi, tidak behavioral, tidak real-time. "
            "Robo-advisor (Bibit): cover alokasi aset, tidak deteksi bias, profil risiko statis. "
            "Mezzi (US): paling dekat — real-time behavioral, tapi US-only, tidak ada counter-evidence "
            "historis, tidak ada friction by design, tidak deteksi FOMO spesifik. "
            "CogniFi adalah satu-satunya yang secara bersamaan: deteksi 3 bias, "
            "intervensi real-time di momen keputusan, counter-evidence berbasis data historis, "
            "friction by design, dan dirancang untuk pasar berkembang Indonesia."
        )
    },
    {
        "id": "system_architecture_flow", "bias": "GENERAL", "category": "prinsip",
        "text": (
            "Arsitektur CogniFi: 4 layer utama. "
            "(1) Bias Detection Engine: extract ticker + sentiment + context dari input user, "
            "classify FOMO / Loss Aversion / Confirmation Bias, score confidence per bias. "
            "(2) Counter Evidence Engine: pull data historis via yfinance, identify episode serupa, "
            "calculate probabilitas koreksi, format counter-evidence. "
            "(3) Intervention Layer: generate pesan intervensi via LLM, attach data historis, "
            "frame pertanyaan reflektif, friction sebelum user bisa lanjut. "
            "(4) Output: bias + confidence, data historis episode serupa, probabilitas, "
            "satu pertanyaan reflektif, disclaimer bukan rekomendasi investasi."
        )
    },
    {
        "id": "idx_universe_saham", "bias": "GENERAL", "category": "data",
        "text": (
            "Universe saham IDX yang di-cover CogniFi: "
            "BBCA.JK (Bank Central Asia), BBRI.JK (Bank Rakyat Indonesia), "
            "TLKM.JK (Telkom Indonesia), ASII.JK (Astra International), "
            "BMRI.JK (Bank Mandiri), UNVR.JK (Unilever Indonesia), "
            "GOTO.JK (GoTo — data mulai 2022 IPO), "
            "BREN.JK (Barito Renewables), EMTK.JK (Elang Mahkota Teknologi), "
            "SIDO.JK (Industri Jamu Sido Muncul). "
            "Data historis via yfinance dengan suffix .JK. "
            "Jika episode < 3 ditemukan, sistem tidak tampilkan probabilitas tapi beri warning."
        )
    },
    {
        "id": "counter_evidence_prinsip", "bias": "GENERAL", "category": "prinsip",
        "text": (
            "Prinsip Counter Evidence Engine: episode-based, bukan model-based. "
            "Tidak menggunakan machine learning atau model prediktif. "
            "Pendekatan: 'Berapa kali kondisi seperti ini terjadi di masa lalu, "
            "dan apa yang terjadi setelahnya?' "
            "Lebih transparan, lebih mudah diverifikasi, lebih bisa dipercaya user awam. "
            "FOMO evidence: cari episode harga naik > threshold dalam window hari, "
            "hitung outcome forward_days hari berikutnya. "
            "Episode terlalu berdekatan difilter (min gap 5 hari) untuk hindari double-counting. "
            "Semua angka dari data aktual Yahoo Finance — tidak ada angka yang dikarang."
        )
    },
    {
        "id": "output_disclaimer_wajib", "bias": "GENERAL", "category": "prinsip",
        "text": (
            "Yang tidak boleh ada di output CogniFi: "
            "Rekomendasi beli atau jual. Prediksi harga masa depan. "
            "Opini tentang kualitas aset. Lebih dari satu pertanyaan reflektif. "
            "Kata 'jangan', 'salah', 'berbahaya', 'kamu harus'. "
            "Disclaimer wajib di setiap output: "
            "'Sistem ini bukan rekomendasi investasi. Output berbasis data historis. "
            "Masa lalu tidak menjamin masa depan. Keputusan investasi sepenuhnya tanggung jawab user.'"
        )
    },
    {
        "id": "friction_checkbox_design", "bias": "GENERAL", "category": "prinsip",
        "text": (
            "Friction by design: setelah output intervensi ditampilkan, user tidak langsung bisa lanjut. "
            "Ada active acknowledgment — checkbox yang menyatakan sudah membaca dan memahami data. "
            "Kenapa checkbox bukan timer? Timer terasa seperti hukuman, user frustrasi. "
            "Checkbox adalah micro-commitment: user secara sadar memilih untuk lanjut. "
            "Secara psikologis lebih efektif dari timer. "
            "Sistem tidak memblokir — user selalu bisa lanjut setelah acknowledge. "
            "Goal: friction cukup untuk System 2 aktif, tidak lebih."
        )
    },
    {
        "id": "problem_statement_presisi", "bias": "GENERAL", "category": "konteks",
        "text": (
            "Pernyataan masalah CogniFi: investor retail Indonesia (mayoritas di bawah 30, "
            "belajar dari sosial media, aktif di pasar volatile) tidak memiliki mekanisme apapun "
            "yang hadir secara real-time pada momen keputusan untuk mendeteksi bias kognitif "
            "yang sedang aktif dan menyajikan counter-evidence sebelum transaksi dieksekusi. "
            "Yang ada hanyalah informasi sebelum keputusan dan penyesalan sesudahnya. "
            "Tidak ada yang mengisi celah di antaranya. "
            "Siklus: keputusan impulsif, kerugian, cognitive dissonance, tahan rugi, "
            "kerugian dalam, experienced regret, keputusan impulsif berikutnya. "
            "Siklus ini hanya bisa diintervensi di titik pertama."
        )
    },
    
]

_client     = None
_collection = None

try:
    import streamlit as st
    _STREAMLIT_AVAILABLE = True
except ImportError:
    _STREAMLIT_AVAILABLE = False


def _get_collection():
    """
    Load ChromaDB collection dengan lazy init + Streamlit cache.
    Jika Streamlit tersedia, gunakan @st.cache_resource agar
    embedding model hanya di-load sekali per server session (P-03).
    Jika tidak (test / standalone), pakai global variable biasa.
    """
    if _STREAMLIT_AVAILABLE:
        return _get_collection_cached()
    return _get_collection_global()


def _get_collection_global():
    """Fallback global cache untuk non-Streamlit context."""
    global _client, _collection
    if _collection is not None:
        return _collection
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    _client  = chromadb.PersistentClient(path=DB_PATH)
    existing = [c.name for c in _client.list_collections()]
    if COLLECTION in existing:
        _collection = _client.get_collection(name=COLLECTION, embedding_function=embed_fn)
        if _collection.count() == 0:
            _collection = _build_collection_with(embed_fn, _client)
    else:
        _collection = _build_collection_with(embed_fn, _client)
    return _collection


if _STREAMLIT_AVAILABLE:
    @st.cache_resource(show_spinner=False)
    def _get_collection_cached():
        """P-03: Cache ChromaDB collection sekali per server session via Streamlit."""
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
        client   = chromadb.PersistentClient(path=DB_PATH)
        existing = [c.name for c in client.list_collections()]
        if COLLECTION in existing:
            col = client.get_collection(name=COLLECTION, embedding_function=embed_fn)
            if col.count() == 0:
                col = _build_collection_with(embed_fn, client)
        else:
            col = _build_collection_with(embed_fn, client)
        return col
else:
    def _get_collection_cached():
        return _get_collection_global()


def _build_collection_with(embed_fn, client):
    """Build collection dengan client yang di-pass (bukan global)."""
    col = client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"}
    )
    col.upsert(
        ids       = [d["id"]       for d in CORPUS],
        documents = [d["text"]     for d in CORPUS],
        metadatas = [{"bias": d["bias"], "category": d["category"]} for d in CORPUS],
    )
    return col


def retrieve_context(query: str, bias_type: str = None, category: str = None, top_k: int = 3) -> list[str]:
    """
    Retrieve top_k chunk paling relevan dari knowledge base CogniFi.

    Args:
        query:     Input investor atau deskripsi situasi bias
        bias_type: "FOMO" | "LOSS_AVERSION" | "CONFIRMATION_BIAS" | "GENERAL" | None
        category:  "teori" | "deteksi" | "intervensi" | "konteks" | "prinsip" | "data" | "persona" | None
        top_k:     Jumlah chunk yang dikembalikan

    Returns:
        List of strings siap diinjeksikan ke prompt LLM.
    """
    col = _get_collection()

    where = None
    if bias_type and category:
        where = {"$and": [{"bias": {"$in": [bias_type, "GENERAL"]}}, {"category": {"$eq": category}}]}
    elif bias_type:
        where = {"bias": {"$in": [bias_type, "GENERAL"]}}
    elif category:
        where = {"category": {"$eq": category}}

    results = col.query(
        query_texts=[query],
        n_results=min(top_k, col.count()),
        where=where,
        include=["documents", "distances"]
    )

    docs, dists = results["documents"][0], results["distances"][0]
    filtered = [doc for doc, d in zip(docs, dists) if d < 0.85]
    return filtered[:top_k]


def retrieve_context_formatted(query: str, bias_type: str = None, category: str = None, top_k: int = 3) -> str:
    """
    Sama seperti retrieve_context tapi return string siap inject ke prompt.
    Prefix '[Konteks N]' pada tiap chunk.
    """
    chunks = retrieve_context(query, bias_type=bias_type, category=category, top_k=top_k)
    if not chunks:
        return "Tidak ada konteks relevan yang ditemukan."
    return "\n\n".join(f"[Konteks {i+1}] {chunk}" for i, chunk in enumerate(chunks))


def retrieve_by_category(category: str, top_k: int = 5) -> list[str]:
    """
    Ambil chunk berdasarkan category spesifik.
    Berguna untuk inject prinsip atau panduan tone ke prompt.
    """
    col = _get_collection()
    results = col.query(
        query_texts=[""],
        n_results=min(top_k, col.count()),
        where={"category": {"$eq": category}},
        include=["documents"]
    )
    return results["documents"][0]


def add_documents(documents: list[dict]) -> None:
    """
    Tambah dokumen baru ke vector store.
    Tiap dict harus punya: id, bias, category, text.
    """
    col = _get_collection()
    col.upsert(
        ids       = [d["id"]   for d in documents],
        documents = [d["text"] for d in documents],
        metadatas = [{"bias": d["bias"], "category": d["category"]} for d in documents],
    )


def reset_db() -> None:
    """Hapus dan rebuild collection dari corpus."""
    global _client, _collection
    # Pastikan global client terinisialisasi dulu
    _get_collection_global()
    if _client:
        _client.delete_collection(COLLECTION)
    _collection = None
    _get_collection_global()
    if _STREAMLIT_AVAILABLE:
        _get_collection_cached.clear()  # clear Streamlit cache juga
    print(f"ChromaDB reset. {len(CORPUS)} chunks di-index ulang.")


def stats() -> dict:
    col = _get_collection()
    return {
        "total_chunks": col.count(),
        "corpus_size":  len(CORPUS),
        "db_path":      DB_PATH,
        "embed_model":  EMBED_MODEL,
        "collection":   COLLECTION,
    }


if __name__ == "__main__":
    print("Initializing ChromaDB dari dokumen CogniFi...\n")
    s = stats()
    for k, v in s.items():
        print(f"  {k}: {v}")
    print()

    test_cases = [
        ("takut ketinggalan, semua orang pada beli, kayaknya mau pump",      "FOMO"),
        ("GOTO mau naik nih, masih sempet ga?",                               "FOMO"),
        ("nyangkut, nunggu balik modal, ini cuma koreksi",                    "LOSS_AVERSION"),
        ("average down biar rata, harga murah sekarang",                      "LOSS_AVERSION"),
        ("BBRI bagus kan? prospeknya bagus banget, benar kan?",               "CONFIRMATION_BIAS"),
        ("semua komunitas bilang saham ini bagus, konsensusnya naik",         "CONFIRMATION_BIAS"),
        ("gimana cara kerja intervensi di sistem ini?",                       "GENERAL"),
        ("kenapa edukasi tidak cukup untuk mengatasi bias kognitif?",         "GENERAL"),
    ]

    print("=" * 60)
    for query, bias in test_cases:
        print(f"\n[{bias}] {query[:55]}...")
        chunks = retrieve_context(query, bias_type=bias, top_k=2)
        for i, chunk in enumerate(chunks, 1):
            print(f"  [{i}] {chunk[:100]}...")

    print("\n" + "=" * 60)
    print(f"Test selesai. {len(CORPUS)} chunks tersedia.")