# YouTubeDownloader

Script Python (`download.py`) untuk mendownload video dan audio YouTube dengan kualitas terbaik, memakai [yt-dlp](https://github.com/yt-dlp/yt-dlp). Hasilnya langsung bisa diputar di **QuickTime Player**, iPhone, dan iPad.

## Kualitas yang didapat

- **Video**: otomatis mengambil resolusi tertinggi (sampai 4K/8K) dan fps tertinggi (60fps).
- **Audio**: stream audio terbaik dari trek bahasa asli (bukan dubbing).
- **Siap QuickTime tanpa mengorbankan kualitas**: pada resolusi tertinggi, script mengutamakan stream H.264/HEVC + AAC yang bisa langsung disalin ke MP4 **tanpa encode ulang**.
- **Jika resolusi tertinggi hanya ada dalam AV1/VP9** (biasanya video 1440p/4K), video dikonversi ke HEVC dengan encoder hardware Mac. Kualitasnya dijaga sangat tinggi: pada pengujian skor VMAF ~98, artinya tidak bisa dibedakan dari aslinya.
- **Lengkap**: judul, channel, tanggal, chapter, dan thumbnail ikut disisipkan ke dalam file.

## Persiapan (sekali saja)

1. Pasang FFmpeg (untuk menggabungkan video + audio) dan Deno (dibutuhkan YouTube agar semua format kualitas tinggi bisa diakses):
   ```bash
   brew install ffmpeg deno
   ```
2. Buat virtual environment dan pasang dependensi:
   ```bash
   python3 -m venv env
   source env/bin/activate
   pip install -U -r requirements.txt
   ```

## Cara pakai

```bash
source env/bin/activate

python download.py "https://youtu.be/VIDEO_ID"            # video kualitas tertinggi, siap QuickTime
python download.py URL -q 1080                            # maksimal 1080p
python download.py URL --original                         # codec asli YouTube tanpa konversi
python download.py URL --audio                            # audio saja, kualitas asli (tanpa konversi)
python download.py URL --audio-format mp3                 # audio saja dalam MP3 kualitas tertinggi
python download.py URL1 URL2                              # beberapa video sekaligus
python download.py PLAYLIST_URL --playlist                # satu playlist penuh
python download.py URL -o ~/Movies                        # simpan ke folder lain
```

Hasil download disimpan di folder `downloads/`. Lihat semua opsi dengan `python download.py --help`.

## Memilih mode

| Kebutuhan | Perintah | Hasil |
|---|---|---|
| Kualitas tertinggi, bisa diputar di QuickTime/iPhone | *(default)* | H.264/HEVC + AAC dalam MP4 |
| Codec asli YouTube tanpa konversi sama sekali (termasuk HDR) | `--original` | AV1/VP9 + Opus dalam MP4, buka dengan [IINA](https://iina.io/) atau [VLC](https://www.videolan.org/) |
| Audio kualitas maksimal | `--audio` | Opus asli (`.opus`) |
| Audio untuk iPhone/Apple Music | `--audio-format m4a` | AAC asli (`.m4a`), tanpa konversi |
| Audio untuk perangkat lama | `--audio-format mp3` | MP3 VBR kualitas tertinggi (~245 kbps) |

Konversi ke HEVC hanya terjadi jika resolusi tertinggi tidak tersedia dalam H.264. Untuk video panjang beresolusi 4K, prosesnya bisa memakan waktu. Kalau tidak mau ada konversi, batasi resolusi dengan `-q 1080` (H.264 biasanya tersedia sampai 1080p) atau pakai `--original`.

Konversi audio ke MP3, FLAC, atau WAV tidak menambah kualitas karena sumbernya dari YouTube sudah terkompresi. Format `best` (default) adalah yang paling bagus.

## Jika download gagal

- Perbarui yt-dlp, karena YouTube sering mengubah sistemnya: `pip install -U -r requirements.txt`
- Untuk video yang dibatasi umur, khusus member, atau kualitas YouTube Premium, pakai login dari browser: `--cookies-from-browser chrome` (atau `safari`, `firefox`).

## Notebook lama

`main.ipynb` berisi percobaan awal (pytube dan yt-dlp) sebelum dirapikan menjadi `download.py`. Sel pytube sudah tidak berfungsi, dan beberapa sel di sana meng-encode ulang video atau mengonversi audio ke MP3 192 kbps sehingga kualitasnya turun. Gunakan `download.py`.

## Catatan

Gunakan hanya untuk video yang Anda miliki haknya atau yang lisensinya mengizinkan untuk didownload, dan patuhi Ketentuan Layanan YouTube.
