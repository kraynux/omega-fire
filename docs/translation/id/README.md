<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-fire.png" alt="Omega-Fire" width="384">
</div>

# 󰦝 OMEGA-FIRE

**Pos manajemen keamanan jaringan terpadu**

> Dikembangkan oleh [kraynux](https://github.com/kraynux) untuk [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Halaman resmi: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Pratinjau: [Tangkapan layar](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🌐 Dokumentasi, ekspor & antarmuka tersedia dalam **17 bahasa** — lihat [Bahasa antarmuka](#bahasa-antarmuka).  
**Bahasa:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

**Omega-Fire** adalah aplikasi TUI (Terminal User Interface) berbasis Python yang dibangun dengan [Textual](https://github.com/Textualize/textual). Dari terminal, aplikasi ini menyediakan satu antarmuka untuk mengelola firewall Linux, Fail2Ban, alamat yang diblokir, aturan jaringan, log, dan statistik sistem.

Antarmuka Textual adalah mode kerja bawaan dan dinavigasi melalui menu, formulir tervalidasi (semua kolom wajib diperiksa sebelum melanjutkan), dan layar khusus, dengan tema, bantuan kontekstual, dan pintasan keyboard yang dipakai bersama seluruh suite OMEGA (omega-check, omega-deep, omega-stress...). Antarmuka [Rich](https://github.com/Textualize/rich) lama, yang berurutan dan dikendalikan dengan mengetik angka, tetap tersedia melalui `--legacy-cli` (lihat [Menjalankan](#menjalankan)). 
Pratinjau: [Tangkapan layar](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/index-2.html)

Proyek ini dirancang mengikuti prinsip **Clean Architecture**, dengan pemisahan yang jelas antara domain bisnis, orkestrasi, infrastruktur, dan antarmuka pengguna.

## Daftar isi

- [Pengenalan](#pengenalan)
- [Fitur](#fitur)
- [Arsitektur](#arsitektur)
- [Prasyarat](#prasyarat)
- [Instalasi](#instalasi)
- [Penggunaan](#penggunaan)
- [Konfigurasi](#konfigurasi)
- [Backend dan kompatibilitas](#backend-dan-kompatibilitas)
- [Persistensi, log, dan ekspor](#persistensi-log-dan-ekspor)
- [Keamanan](#keamanan)
- [Pengujian dan kualitas](#pengujian-dan-kualitas)
- [Status proyek](#status-proyek)
- [Pencopotan](#pencopotan)
- [Lisensi](#lisensi)

---

## Pengenalan

Omega-Fire berperan sebagai **pos kendali lokal** untuk keamanan jaringan. Aplikasi ini otomatis mendeteksi komponen yang ada di mesin dan menyesuaikan menu dengan kemampuan yang benar-benar tersedia.

### Tujuan

- Menyatukan nftables, iptables, ip6tables, dan Fail2Ban dalam antarmuka yang konsisten.
- Memudahkan pengamatan dan tindakan atas koneksi, pemblokiran, dan peristiwa sistem.
- Memusatkan ekspor, cadangan, audit, dan riwayat operasi.
- Menjaga arsitektur yang dapat diuji dan diperluas.
- Tetap berjalan dalam mode terbatas jika komponen opsional tidak ada.

### Yang dilakukan Omega-Fire

- Mendeteksi backend, layanan, kernel, dan alat yang tersedia.
- Mengelola nftables, iptables, dan ip6tables jika komponen tersebut ada.
- Mengelola IP yang diblokir, satu per satu atau secara massal, dengan impor, ekspor, sinkronisasi, dan flush.
- Membuat, menampilkan, dan menghapus aturan lanjutan.
- Menerapkan kebijakan bawaan dengan cadangan otomatis sebelumnya.
- Mengelola jail Fail2Ban dan pemblokirannya.
- Menganalisis log secara langsung atau dalam bentuk statistik.
- Menyediakan pengawasan dalam bentuk monitoring.
- Menggunakan conntrack untuk menampilkan koneksi aktif jika tersedia.
- Menghasilkan ekspor JSON, TXT, dan HTML.
- Mencadangkan dan memulihkan seluruh status dalam arsip `.tar.gz`.
- Mencatat operasi dalam log aplikasi dan audit JSON terstruktur.
- Memantau layanan dan aplikasi yang terdeteksi: systemd, runit, OpenRC, Docker, server, VNC, dan sebagainya.

### Yang tidak dilakukan proyek ini

- Tidak menggantikan nftables, iptables, atau Fail2Ban.
- Bukan firewall mandiri yang terpisah dari sistem.
- Tidak menyediakan autentikasi multipengguna.
- Tidak membuka API jaringan dalam operasi normal.
- Bukan dashboard web.
- Tidak melindungi mesin jarak jauh secara langsung dari mesin lain.
- Secara bawaan tidak memasang file apa pun di luar foldernya sendiri.
- Tidak menjamin ketersediaan semua backend di semua distribusi.

---

## Fitur

### 1. Kemampuan dan diagnostik

- Menampilkan registri kemampuan yang terdeteksi.
- Melihat detail suatu kemampuan berdasarkan pengenalnya.
- Pemindaian ulang sistem secara manual setelah memasang komponen.
- Melihat diagnostik terbaru.
- Melihat dan mencari di log aplikasi.
- Mengekspor status dan diagnostik ke JSON, TXT, atau HTML.
- Kategori **Suite omega**: omega-serv (instans yang terdeteksi dan berjalan), omega-waf (ekstra `magnet` aktif) dan omega-jail (jail yang terpasang), terlihat di registri, dashboard, dan laporan.

### 2. Manajemen IP terpadu

Blacklist terpadu memungkinkan bekerja dengan nftables dan iptables dari satu layar yang sama.

- Memblokir satu IP atau daftar IP.
- Membuka blokir satu per satu atau secara massal.
- Input langsung atau impor dari file.
- Daftar per backend atau tampilan terpadu.
- Sinkronisasi antara backend NFTables/IPTables.
- Ekspor dan impor ulang daftar.
- Pembersihan penuh satu atau beberapa backend.
- Dukungan IPv4 dan IPv6.
- Mengelola file blocklist (`var/blocklist/`) beserta item yang disematkan langsung dari layar khusus.

### 3. Manajemen aturan dan kebijakan

- Wizard langkah demi langkah untuk membuat aturan lanjutan.
- Daftar aturan sistem dan aturan yang dibuat oleh Omega-Fire.
- Menghapus aturan melalui pemilihan.
- Pembersihan otomatis aturan nonaktif di basis referensi.
- Pembersihan dan sinkronisasi ulang basis data dengan firewall sebenarnya, dengan pratinjau dan cadangan terlebih dahulu, tanpa pernah mengubah firewall itu sendiri.
- Aturan dari alat lain (UFW, Tailscale, Docker…) dikenali dari asalnya: ditampilkan sebagai informasi, tidak pernah dihapus dari Omega-Fire.
- Pengaman sebelum menerapkan kebijakan atau mengosongkan iptables saat alat lain memiliki aturan di sana: terapkan di semua tempat, hanya di nftables, atau batalkan — konsekuensinya dijelaskan rinci di bantuan.
- Menerapkan kebijakan bawaan.
- Cadangan otomatis sebelum menerapkan kebijakan.
- Menyesuaikan, menyimpan, dan memulihkan kebijakan.
- Penanda kebijakan aktif di menu status dan dashboard.
- Penanda profil yang diubah dalam bentuk `Profil + CUSTOM`.
- Pengelolaan tabel (menu 3.5): diagnostik hanya baca per backend (keberadaan tabel, kebijakan input/output/forward, jumlah aturan) dengan penjelasan kebijakan yang berbeda antar-backend (efek nyata, penyebab, dan solusi).
- Inisialisasi tabel nftables pada penggunaan pertama, tanpa pernah menimpa chain yang sudah dikonfigurasi.
- Mengatur ulang kebijakan chain ke ACCEPT di suatu backend, untuk memperbaiki kebijakan restriktif yatim yang ditinggalkan profil sebelumnya.
- Pengosongan terarah satu backend atau pengosongan tersinkron semua backend yang terdeteksi dalam satu tindakan.
- Penghapusan penuh tabel nftables (tindakan lanjutan, di luar aturan saja).

### 4. Manajemen Fail2Ban

- Status rinci jail dan parameternya.
- Jumlah IP yang diblokir dan informasi rate-limit.
- Mencari IP di jail.
- Ban dan unban tunggal atau ganda.
- Memindahkan IP antara jail, backend, dan file.
- Pembuatan jail kustom terpandu.
- Templat jail bawaan, dapat diubah dan dihapus.
- Asal setiap jail: Omega-Fire, omega-jail, konfigurasi utama fail2ban, atau file lain.
- Penghapusan jail yang andal, apa pun nama filenya: peringatan untuk jail yang dipasang oleh omega-jail, penolakan beserta alasan untuk jail dari `jail.local` atau dari file bersama, filter standar fail2ban tidak pernah dihapus.
- Mengosongkan jail atau pembersihan umum.
- Ekspor ke JSON, TXT, atau HTML.
- Pemeriksaan dan audit konfigurasi.
- Kontrol layanan: status, mulai, berhenti, mulai ulang, aktifkan dan nonaktifkan saat boot; setelah dimulai atau dihentikan, registri kemampuan dan dashboard diperbarui.

### 5. Log dan pemeliharaan

- **Pustaka log** (5.1): impor otomatis log dari instans omega-serv yang terdeteksi, termasuk log omega-waf, penyematan path secara manual, dan pengambilan log jarak jauh melalui SSH (kunci atau agen, tidak pernah kata sandi).
- **Favorit** (5.2): menggabungkan log dari Pustaka, menyimpannya dengan nama dan penampil, lalu menjalankannya langsung.
- **Lihat log** (5.3): satu log tanpa konfigurasi, dengan penampil pilihan Anda — Sederhana (dashboard waktu nyata), Klasik (baris terakhir lalu diikuti langsung) atau `lnav`.
- Integrasi `lnav`: beberapa log digabungkan menjadi satu tampilan kronologis, dibungkus header/footer Omega-Fire (lihat [Navigasi](#navigasi)).
- Analisis IP yang paling sering muncul dengan Top N, dapat diekspor untuk dimuat ulang ke pembersihan terarah.
- Pembersihan terarah satu atau beberapa IP di file LOG atau TXT, diketik manual atau dicentang dari sebuah ekspor.
- File tersemat dengan **preset yang bisa dicentang**: hanya path umum yang benar-benar ada di mesin yang ditawarkan.
- Rotasi dan pencadangan segera atau otomatis.
- Memulihkan cadangan.
- Pembersihan berdasarkan usia, kuota, jenis, atau pilihan manual.
- Pembersihan lanjutan per folder atau lingkungan.
- Statistik 24 jam, 7 hari, atau 30 hari.
- Analisis peristiwa, pergerakan, kuota, dan IP yang ada di jail.

### 6. Ekspor dan laporan

Format yang tersedia:

- **JSON**: data terstruktur dan dapat digunakan ulang.
- **TXT**: format mentah atau disesuaikan untuk injeksi.
- **HTML**: laporan yang mudah dibaca dan visual.

Laporan yang tersedia:

- Blacklist lengkap.
- Ruleset terstruktur.
- Aturan yang dipilih berdasarkan asal: sistem, Omega-Fire, atau aktif.
- Laporan audit lengkap.
- Statistik Fail2Ban.
- Status dan diagnostik sistem.
- Laporan statistik 7 atau 30 hari.
- Peringkat Top N IP.
- Panduan bantuan dan FAQ.

**Lihat semua ekspor** (6.5): semua file yang diekspor di satu tempat, dengan jenis, tanggal, dan ukuran; laporan HTML terbuka di peramban web bawaan pengguna, file JSON atau TXT dibaca di dalam Omega-Fire, tanpa terminal maupun pengelola file.

Tema HTML:

- `omega-base` — biru malam dan sian, tema bawaan.
- `omega-burn` — bara merah-jingga.
- `omega-neon` — cyberpunk sian dan magenta.
- `light-basic` — terang dan sederhana.
- `light-alt` — kertas krem dan hijau hutan.

Bahasa ekspor: diatur terpisah di pengaturan (bawaan « Sama dengan antarmuka »), untuk menyerahkan laporan dalam bahasa pembacanya tanpa mengubah bahasa antarmuka.

### 7. Sistem dan persistensi

- Pencadangan seluruh status: aturan, blokir nftables, blokir iptables, dan Fail2Ban.
- Pembuatan arsip `.tar.gz` bercap waktu.
- Daftar dan pemulihan snapshot: hanya aturan Omega-Fire yang dapat dibuat ulang secara identik yang dipasang kembali; aturan alat lain tidak pernah disentuh.
- Riwayat tindakan.
- Penyaringan dan pembersihan riwayat.
- Memuat ulang konfigurasi dan memindai ulang tanpa memulai ulang.

### 8. Monitoring dan statistik

- Dashboard waktu nyata dengan penyegaran berkala (setiap 2 detik), tanpa memblokir antarmuka selama pengumpulan.
- Tampilan kebijakan aktif.
- Koneksi aktif melalui conntrack.
- Lalu lintas, peristiwa, statistik, dan log server.
- Laporan gabungan 7 dan 30 hari.
- Ekspor HTML snapshot dan laporan.

### 9. Pengaturan

- Memilih tema aktif dari sepuluh tema `omega-*` yang dipakai bersama seluruh suite (lihat [Tema dan terminal](#tema-dan-terminal)), tersimpan di antara dua kali peluncuran.
- Menimpa profil tampilan secara manual (otomatis, lengkap, standar, ringkas, atau hanya mono), diterapkan pada peluncuran berikutnya.
- Bahasa antarmuka dari 17 bahasa (lihat [Bahasa antarmuka](#bahasa-antarmuka)): hanya antarmuka yang dimulai ulang; aturan firewall, Fail2Ban, dan layanan tidak tersentuh.
- Bahasa ekspor HTML dan TXT, terpisah dari bahasa antarmuka.
- Folder ekspor dan tangkapan layar yang dapat diubah, dengan pengosongan setelah konfirmasi.
- Dapat diakses dari menu utama (`9. PENGATURAN`) atau langsung dengan tombol `s`.

### 10. Bantuan

- **Panduan bantuan**: semua lembar bantuan dikumpulkan sesuai urutan menu, setiap lembar membuka lembar terkaitnya.
- **FAQ**: pertanyaan nyata yang ditemui saat digunakan (aturan alat lain, pemulihan, Fail2Ban, log, ekspor, dan peramban).
- Ekspor HTML panduan dan FAQ, dalam bahasa ekspor.
- Tombol `a` tetap menjadi bantuan layar saat ini.

---

## Arsitektur

```text
src/omega_fire/
├── app/              Bootstrap dan kontainer injeksi dependensi
├── core/             Kemampuan, enumerasi, dan pengecualian
├── domain/           Logika bisnis murni: aturan, IP, jail, log
├── application/      Orkestrasi: commands dan queries
├── infrastructure/   Backend, penyimpanan, ekspor, log, dan sensor sistem
├── ports/            Kontrak Protocol/ABC
├── interfaces/       interfaces/tui/ (Textual, bawaan) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Ekstensi bawaan: nftables, iptables, Fail2Ban, conntrack
└── shared/           Parsing, jaringan, pemformatan, dan utilitas lintas lapisan
```

### Prinsip desain

- `domain/` tidak berisi I/O maupun dependensi ke infrastruktur.
- `application/` mengorkestrasi kasus penggunaan melalui domain dan port — layar Textual dan tindakan antarmuka Rich memanggil commands/queries yang sama, dan logika bisnis tidak bergantung pada salah satu dari kedua antarmuka.
- `infrastructure/` adalah satu-satunya lapisan yang boleh memanggil `nft`, `iptables`, `fail2ban-client`, dan alat eksternal lainnya (subprocess, pty, file).
- `interfaces/` tidak boleh memanggil `subprocess` secara langsung.
- `ports/` mendefinisikan kontrak yang diharapkan adaptor.
- `core/` menyediakan registri kemampuan yang dipakai berbagai lapisan.
- Plugin memungkinkan penambahan atau pengembangan backend tanpa mengubah domain bisnis.
- Antarmuka Textual (`interfaces/tui/`) bertumpu pada [`omega-lib`](https://github.com/) (dependensi bersama seluruh suite OMEGA: tema 9 token, deteksi terminal, kontrak port bersama), tidak diterbitkan di PyPI — disertakan dalam arsip distribusi (`vendor/omega-lib/`, lihat [Instalasi](#instalasi)).
- Setiap panggilan yang berpotensi lambat (backend firewall, `fail2ban-client`, disk) yang dipicu dari layar Textual dijalankan di latar belakang (thread), tidak pernah di thread utama antarmuka — dashboard atau formulir tetap responsif selama operasi alih-alih membekukan seluruh aplikasi.

### Struktur data

Omega-Fire menggunakan SQLite melalui pustaka standar `sqlite3`, tanpa ORM eksternal. Himpunan data utama mencakup blokir, aturan, peristiwa audit, dan snapshot.

Migrasi diberi versi dan diterapkan otomatis saat aplikasi dimulai.

---

## Prasyarat

### Sistem

- Linux, terutama Arch Linux dan distribusi yang kompatibel.
- Python 3.10 atau lebih baru.
- Hak root tersedia melalui `sudo`.
- Pengelola layanan: systemd, runit, atau OpenRC.
- Setidaknya satu backend firewall: nftables atau iptables.
- Terminal minimal 80x24 (lihat [Tema dan terminal](#tema-dan-terminal) untuk rincian profil tampilan sesuai ukuran yang tersedia).

### Dependensi Python

Dependensi produksi didefinisikan dalam `requirements.txt`:

- `textual` — antarmuka TUI bawaan.
- `omega-lib` — tema, deteksi terminal, dan kontrak yang dipakai bersama suite OMEGA (tidak diterbitkan di PyPI, lihat [Arsitektur](#arsitektur) dan [Instalasi](#instalasi)).
- `rich` — tampilan antarmuka `--legacy-cli` dan beberapa laporan.
- `psutil` — informasi sistem (CPU, memori, jaringan, proses) untuk dashboard dan diagnostik.
- `jinja2` — pembuatan ekspor HTML.
- `python-dotenv` — variabel lingkungan.
- `pyte` — emulator terminal virtual, untuk membungkus `lnav` (menu 8.6 dan penampil lnav di 5.2 / 5.3).

Alat kualitas (`pytest`, `black`, `flake8`, `mypy`) dicantumkan sebagai komentar di `requirements.txt`: hapus komentarnya atau pasang secara terpisah jika Anda berkontribusi pada proyek (lihat [Pengujian dan kualitas](#pengujian-dan-kualitas)).

### Alat opsional yang disarankan

Aplikasi berjalan dalam mode terbatas jika alat-alat ini tidak ada:

- `fail2ban` — pemblokiran otomatis.
- `conntrack` atau `conntrack-tools` — koneksi aktif dan statistik jaringan.
- `lnav` — analisis log lanjutan untuk banyak file.

Di Arch Linux dan turunannya:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Instalasi

Arsip resmi disediakan dalam format `.tar.gz`. Periksa integritasnya sebelum instalasi:

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **Ketiga metode ini untuk instalasi pertama.** Jika `~/omega-fire` sudah ada (pembaruan dari versi sebelumnya), gunakan bagian [Pembaruan](#pembaruan) di bawah — jangan pernah menjalankan ulang perintah ini dari dalam folder `omega-fire` yang sudah ada: `tar` akan mencoba membuat `omega-fire/omega-fire/` bersarang dan gagal dengan kesalahan izin jika folder itu milik root (sering terjadi jika ekstraksi sebelumnya tidak sengaja dilakukan dengan `sudo tar`).

### Metode 1 — skrip instalasi

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Tampaknya Anda sudah berada di folder omega-fire — lihat bagian Pembaruan di README." >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ Sudah diekstrak di sini, langkah dilewati." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire sudah ada, pemindahan dilewati." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Menjalankan:

```bash
./omega-fire.sh
```

Jika alias telah dipasang, buka terminal baru lalu gunakan:

```bash
fire
```

### Metode 2 — instalasi lengkap yang tangguh

Perintah ini dapat dijalankan ulang: perintah ini melewati langkah yang sudah dilakukan.

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Tampaknya Anda sudah berada di folder omega-fire — lihat bagian Pembaruan di README." >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire sudah ada, ekstraksi dilewati." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv sudah ada, langkah dilewati." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ Grup omega-fire sudah ada." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER sudah menjadi anggota grup omega-fire." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire terpasang. Jalankan ./omega-fire.sh."
```

### Metode 3 — instalasi terperinci

```bash
# 0. Memastikan tidak menjalankan ulang dari dalam omega-fire yang sudah ada
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Tampaknya Anda sudah berada di folder omega-fire — lihat bagian Pembaruan di README." >&2; exit 1; }

# 1. Ekstrak
[ -d omega-fire ] && echo "ℹ️ Sudah diekstrak di sini, langkah dilewati." || tar -xzf omega-fire.tar.gz

# 2. Pindahkan ke home
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire sudah ada, pemindahan dilewati." || mv omega-fire ~/

# 3. Masuk ke proyek
cd ~/omega-fire/

# 4. Buat lingkungan virtual
[ -d .venv ] && echo "ℹ️ .venv sudah ada, pembuatan dilewati." || python3 -m venv .venv

# 5. Pasang dependensi (omega-lib yang disertakan, jika ada, sebelum requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. Jadikan peluncur dapat dieksekusi
chmod +x omega-fire.sh

# 7. Siapkan var/ untuk root dan pengguna saat ini
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Jalankan
./omega-fire.sh
```

`vendor/omega-lib/` hanya ada di arsip resmi (`build-release.sh` menyertakannya secara otomatis, karena omega-lib tidak diterbitkan di PyPI); pada clone pengembangan, pasang secara terpisah dari repositorinya sendiri (`pip install -e path/ke/omega-lib`).

Grup khusus dan bit `setgid` memungkinkan root dan pengguna berbagi file yang dihasilkan di `var/` tanpa membuka izin untuk seluruh sistem. Login ulang atau `newgrp omega-fire` mungkin diperlukan agar keanggotaan grup langsung berlaku.

### Pembaruan

Jika `~/omega-fire` sudah ada (instalasi sebelumnya), **jangan pernah menjalankan ulang perintah instalasi dari dalam folder ini**: `tar` akan mencoba membuat `omega-fire/omega-fire/` bersarang dan gagal, biasanya dengan rentetan kesalahan « Izin ditolak » jika folder itu milik `root` (sering terjadi jika ekstraksi sebelumnya tidak sengaja dilakukan dengan `sudo tar`).

Prosedur yang disarankan, dari folder mana pun **selain `~/omega-fire`** (biasanya `~` itu sendiri):

```bash
# 1. Periksa status dan pemilik instalasi yang ada
ls -ld ~/omega-fire

# 2. Sisihkan instalasi lama alih-alih menimpanya
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. Ekstrak arsip baru langsung ke home
tar -xzf omega-fire.tar.gz -C ~/

# 4. Pasang ulang (membuat ulang venv, memasang ulang dependensi, mengatur ulang izin var/)
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. Jalankan
./omega-fire.sh
```

Langkah 4 (`./install.sh`) otomatis mendeteksi kasus ini (basis data `var/db/` tidak ada di sini, folder `~/omega-fire.old-YYYYMMDD` ditemukan tepat di sebelahnya) dan **memulihkan sendiri** `config/omega-fire.conf`, basis data, blocklist, cadangan, ekspor, dan tangkapan layar dari instalasi lama — tanpa pertanyaan, tanpa langkah manual. Tidak ada yang perlu dilakukan selain langkah 1 sampai 5 di atas, apa pun isi instalasi Anda sebelumnya.

Jika ada beberapa folder di sebelahnya yang tampak seperti instalasi lama (ambigu), `install.sh` tidak menebak apa pun: ia menampilkan path-nya dan mempersilakan Anda menjalankan sendiri `sudo ./migrate-state.sh <folder>` setelah sumber yang benar teridentifikasi.

Setelah instalasi baru dipastikan berfungsi, folder lama `~/omega-fire.old-YYYYMMDD` dapat dihapus (`sudo rm -rf ~/omega-fire.old-YYYYMMDD`).

### Alias Bash atau Zsh

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Lalu muat ulang shell:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Ikon dan simbol Nerd Fonts

Jika ikon tidak tersedia, pasang simbol Nerd Fonts:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Penggunaan

### Menjalankan

```bash
cd ~/omega-fire
./omega-fire.sh

# atau cukup, jika alias telah dibuat:
fire
```

Peluncur:

1. Memeriksa hak root dan menjalankan ulang melalui `sudo` jika perlu.
2. Mendeteksi `.venv`, `venv`, atau Python sistem.
3. Mengatur `PYTHONPATH` ke `src/`.
4. Menjalankan `python -m omega_fire` — antarmuka **Textual**, secara bawaan.

Untuk menjalankan antarmuka Rich lama (input angka berurutan) sebagai gantinya:

```bash
./omega-fire.sh --legacy-cli
```

Antarmuka lama tetap antarmuka versi 3.0, dalam bahasa Prancis: menu 5 asli (tanpa Pustaka, Favorit, atau penampil Klasik), tanpa "Lihat semua ekspor", tanpa panduan bantuan maupun FAQ, tanpa preset. Antarmuka Textual memuat versi 3.5 lengkap.

### Bahasa antarmuka

17 bahasa: Prancis, Inggris, Spanyol, Portugis (Brasil), Italia, Jerman, Belanda, Polandia, Rusia, Tionghoa, Vietnam, Thai, Indonesia, Jepang, Korea, Hindi, Arab. Dipilih di pengaturan (tombol `s`, « Langue / Language », label yang tidak pernah diterjemahkan), diterapkan dengan memulai ulang antarmuka saja, atau sesekali dengan `OMEGA_FIRE_LANG=id ./omega-fire.sh` (dipertahankan melalui `sudo` oleh peluncur). Di konsol teks Linux (TTY), bahasa yang aksaranya tidak ada di font konsol (Vietnam, Tionghoa, Thai, Jepang, Korea, Hindi, Arab) ditampilkan dalam bahasa Inggris selama sesi tersebut. Bahasa Arab ditampilkan dari kanan ke kiri. Dalam bahasa Hindi, Terminator, GNOME Terminal, Xfce Terminal, dan Alacritty menampilkan teks yang rata; terminal yang menyusun sendiri huruf gabungan (Kitty, Ghostty, Konsole) dapat menggeser bingkai dan kolom. **Bahasa ekspor** (laporan HTML dan TXT) diatur terpisah, bawaannya « Sama dengan antarmuka ». Log aplikasi dan riwayat audit tetap dicatat dalam bahasa Prancis; judul riwayat ditampilkan dalam bahasa yang dipilih. Antarmuka lama (`--legacy-cli`) tetap dalam bahasa Prancis.

### Alur umum

1. Layar pembuka (splash), lalu peringatan jika terminal terlalu kecil.
2. Deteksi kemampuan sistem (layar khusus, tidak memblokir).
3. Menu utama: 8 bagian tematik (1-8), pengaturan (9), dan bantuan (10).
4. Pilih bagian, lalu tindakan — setiap tindakan membuka formulir yang semua kolom wajibnya divalidasi sebelum melanjutkan.
5. Konfirmasi eksplisit sebelum operasi sensitif atau destruktif apa pun (flush, pembersihan, pemulihan...).
6. Eksekusi di latar belakang untuk operasi yang lambat (antarmuka tetap dapat dipakai selama menunggu), lalu kembali ke menu dengan ringkasan hasil.

### Navigasi

- Panah atas/bawah: memindahkan kursor di daftar atau menu.
- Tab / Shift+Tab: berpindah antar-kolom formulir.
- Enter: memilih atau memvalidasi.
- Klik baris tabel: memilihnya dan mengisi otomatis kolom terkait (sumber yang akan disematkan, jail tujuan, dan sebagainya).
- `Esc`: kembali ke layar sebelumnya (meminta konfirmasi keluar dari layar utama).
- `a`: bantuan kontekstual — menjelaskan aksi yang sedang berjalan, atau semua aksi di bagian saat ini jika belum ada layar aksi yang terbuka; panduan lengkap dan FAQ ada di menu 10.
- `t`: beralih ke tema berikutnya, tanpa konfirmasi.
- `r`: mendeteksi ulang ukuran dan jenis terminal.
- `s`: membuka pengaturan (tema, profil tampilan, bahasa, folder).
- `q` / `Ctrl+Q`: keluar, dengan konfirmasi.

#### Kekhususan layar lnav (8.6, dan penampil lnav di 5.2 / 5.3)

`lnav` dibungkus dalam pseudo-terminal dengan header/footer Omega-Fire yang tetap di sekeliling tampilannya, untuk mencegah bentrokan antara pintasan bawaannya dan pintasan Omega-Fire:

- Panah ↑↓: bernavigasi di log (pintasan bawaan `lnav`, diteruskan apa adanya).
- Panah ←→: menggulir horizontal pada baris panjang (pintasan bawaan `lnav`).
- `g` / `G`: menuju awal / akhir (pintasan bawaan `lnav`).
- `Ctrl+C`: menandai baris saat ini dan menyalinnya ke clipboard sistem (menggantikan perintah salin bawaan `lnav`, yang bisa macet di beberapa sistem).
- `t` kecil: tema berikutnya, khusus tampilan ini (`T` besar tetap menjadi pintasan bawaan `lnav` untuk menampilkan waktu antarbaris).
- `Ctrl+Q`: kembali ke Omega-Fire (menutup `lnav` dengan rapi, tanpa keluar dari aplikasi).

---

## Tema dan terminal

Sepuluh tema `omega-*` dipakai bersama seluruh suite OMEGA:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Beralih antartema dengan `t`, atau pilih langsung dari pengaturan (`s`).
- Tema yang dipilih disimpan dan dipakai lagi pada peluncuran berikutnya.
- Omega-Fire otomatis menyesuaikan kompleksitas visual (bingkai, splash, kepadatan informasi) dengan terminal yang terdeteksi melalui **profil tampilan**: Lengkap, Standar, Ringkas, atau Mono (hanya ASCII). Profil dapat ditimpa secara manual dari pengaturan.

| Ukuran minimum | Profil | Terminal umum |
|---|---|---|
| 120×32 atau lebih | Lengkap | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 atau lebih | Standar | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 atau lebih | Ringkas | urxvt, xterm, SSH modern |
| di bawah 80×24 | Mono (hanya ASCII) | Linux TTY, SSH lama |

Di bawah 80×24, peluncuran ditolak (ukuran minimum diperlukan); ubah ukuran terminal lalu jalankan ulang, atau gunakan `r` setelah mengubah ukuran jika tampilan tidak diperbarui otomatis.

---

## Konfigurasi

Konfigurasi khusus dapat disesuaikan di:

```text
omega-fire/config/omega-fire.conf
```

Konfigurasi ini dapat mendefinisikan antara lain:

- path log;
- server dan sumber monitoring;
- backend yang tersedia atau path kustom;
- lingkungan yang akan dianalisis;
- parameter yang disesuaikan dengan instalasi tertentu.

Konfigurasi dibaca ulang saat dimulai ulang atau saat pemindaian ulang manual (menu 1.3 atau 7.4).

File ini sepenuhnya opsional (aplikasi tetap berjalan normal tanpanya, dengan beralih ke variabel lingkungan) dan **dikecualikan dari arsip distribusi** — pembaruan tidak pernah menimpanya diam-diam, dan `install.sh` otomatis memulihkannya sendiri dari instalasi lama bila ada (lihat « Pembaruan » di atas).

### Path internal dan path sistem

Secara bawaan, Omega-Fire bekerja di foldernya sendiri:

```text
var/exports/       # folder internal proyek
/var/exports/      # path absolut sistem
```

Jadi `/` di awal itu bermakna. Impor dan ekspor ke sistem harus diminta secara eksplisit oleh pengguna.

---

## Backend dan kompatibilitas

Omega-Fire mendeteksi komponen dan hanya mengaktifkan fitur yang dapat dipakai.

| Komponen | Peran | Status |
|---|---|---|
| nftables | Firewall IPv4/IPv6 modern | Disarankan |
| iptables | Firewall IPv4 | Kompatibel |
| ip6tables | Firewall IPv6 dengan iptables | Kompatibel jika tersedia |
| Fail2Ban | Jail dan pemblokiran otomatis | Opsional |
| conntrack | Koneksi aktif | Opsional |
| lnav | Analisis log lanjutan | Opsional |
| systemd, runit, OpenRC | Manajemen layanan | Deteksi otomatis |
| Docker, VNC, server | Aplikasi dan layanan yang terdeteksi | Tergantung instalasi |

### IPv4 dan IPv6

Kedua keluarga alamat didukung oleh backend yang kompatibel:

- nftables: IPv4 dan IPv6 dalam dual stack;
- iptables/ip6tables: tergantung binari yang tersedia;
- Fail2Ban: tergantung konfigurasi jail dan sistem.

Format IPv6 panjang, terkompresi, lokal, campuran, dengan nol, dan dalam notasi CIDR ditangani oleh komponen terkait.

---

## Persistensi, log, dan ekspor

### Persistensi

- SQLite melalui `sqlite3`.
- Tabel terkait blokir, aturan, audit, dan snapshot.
- Migrasi berversi yang diterapkan otomatis.
- Arsip status lengkap dalam format `.tar.gz`.
- Item yang disematkan (sumber log favorit) dan riwayat terbaru disimpan dalam JSON (`var/runtime/`), tetap ada setelah dimulai ulang.

### Log

- Log teks aplikasi: `var/logs/app.log`.
- Log audit JSON terstruktur yang antara lain berisi `event_type`, `actor`, `action`, `result`, dan `details`.

### Ekspor

Ekspor tersedia dalam JSON, TXT, dan HTML, dengan beberapa tema CSS untuk laporan HTML.

---

## Keamanan

Omega-Fire bekerja pada komponen sistem yang kritis dan harus digunakan dengan hati-hati.

- Menjalankan aplikasi memerlukan hak root melalui `sudo`.
- Flush, pembersihan umum, dan penerapan kebijakan dapat bersifat destruktif.
- Kebijakan bawaan memicu pencadangan otomatis sebelum perubahan.
- Di iptables / ip6tables, menerapkan kebijakan atau mengosongkan backend juga menghapus aturan alat lain (UFW…): Omega-Fire memberitahukannya dan membiarkan Anda memilih sebelum bertindak.
- Lakukan pencadangan manual sebelum setiap perubahan besar.
- Periksa status nyata firewall, jail, dan koneksi setelah setiap operasi.
- Uji terlebih dahulu pada mesin atau target sekali pakai.
- Gunakan jaringan dokumentasi RFC 5737 untuk uji IPv4: `192.0.2.0/24`, `198.51.100.0/24`, dan `203.0.113.0/24`.
- Periksa ekspor dan snapshot sebelum memulihkannya di mesin produksi.
- Jangan memberi folder `var/` izin yang lebih luas dari yang diperlukan.

---

## Pengujian dan kualitas

Rangkaian ini berisi 137 unit test (lebih dari 8.000 kasus diperiksa): domain bisnis, orkestrasi (`application/`), infrastruktur, serta layar Textual yang ditambahkan atau diperbaiki di 3.5, dijalankan dengan stylesheet sebenarnya (tata letak, alur lengkap, bahasa ekspor). Arsip ini tidak menyertakan folder `tests/`: ambil dari repositori pengembangan Anda jika perlu menjalankannya.

```bash
source .venv/bin/activate
python -m unittest discover -s tests/unit -t .
```

Arsitektur berlapis memisahkan domain bisnis dari presentasi secara ketat (`domain/`, `application/`, `ports/` sebagai `Protocol`, lihat [Arsitektur](#arsitektur)): sebagian besar tes tidak memerlukan root maupun firewall sungguhan.

Jika Anda berkontribusi pada proyek, pasang alat kualitas yang dideklarasikan (sebagai komentar) di `requirements.txt`:

```bash
pip install pytest pytest-cov black flake8 mypy
```

Alat yang tersedia setelah dipasang:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## Status proyek

### Poin yang sudah berjalan

- TUI Textual terpadu untuk mekanisme keamanan jaringan utama, formulir tervalidasi, tema, dan bantuan kontekstual yang dipakai bersama suite OMEGA.
- Antarmuka Rich historis dipertahankan sebagai cadangan (`--legacy-cli`).
- Deteksi kemampuan otomatis.
- Manajemen backend yang tersedia.
- Dukungan IPv4/IPv6 sesuai alat yang tersedia.
- Pencatatan log aplikasi dan audit.
- Pencadangan dan pemulihan.
- Ekspor JSON, TXT, dan HTML.
- Dashboard dan statistik, disegarkan di latar belakang tanpa memblokir antarmuka.
- Arsitektur berlapis yang terdokumentasi.

### Keterbatasan yang diketahui

- Rangkaian tes mencakup layar Textual 3.5, belum seluruh layar yang lebih lama (lihat [Pengujian dan kualitas](#pengujian-dan-kualitas)).
- Mekanisme `ExecutionPlan`/`PipelineStep` masih sebagian ada di proyek.
- Ketersediaan pasti fitur bergantung pada binari, layanan, izin, dan konfigurasi mesin host.
- Antarmuka Rich historis (`--legacy-cli`) tidak lagi menjadi fokus pengembangan aktif; antarmuka ini dipertahankan sampai antarmuka Textual sepenuhnya andal dalam kondisi nyata.

---

## Pencopotan

Jika data masih berada di folder proyek:

```bash
sudo rm -rf ~/omega-fire
```

Hapus secara manual file yang diekspor ke tempat lain, alias `fire` yang mungkin ditambahkan di `~/.bashrc` atau `~/.zshrc`, serta grup khusus jika tidak dipakai lagi:

```bash
sudo groupdel omega-fire
```

Jalankan perintah terakhir ini hanya jika tidak ada file atau layanan lain yang bergantung pada grup ini.

---

## Lisensi

Omega-Fire didistribusikan di bawah lisensi **MIT**. Lihat file [`LICENSE`](../../../LICENSE) untuk teks lengkapnya.

---

> **Omega-Fire — Mengamati, mengendalikan, mengaudit, mengamankan.**
>
> Antarmuka TUI terpadu untuk nftables, iptables, ip6tables, Fail2Ban, log, dan monitoring jaringan.
