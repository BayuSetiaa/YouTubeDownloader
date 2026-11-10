# YouTubeDownloader

Script Python (`download.py`) untuk mendownload video dan audio YouTube dengan kualitas terbaik, memakai [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Kualitas yang didapat

- **Video**: otomatis mengambil resolusi tertinggi (sampai 4K/8K), fps tertinggi (60fps), HDR jika ada, dan codec terbaik (AV1 > VP9 > H.264), termasuk format bitrate tinggi jika tersedia.
- **Audio**: stream audio terbaik (biasanya Opus) dari trek bahasa asli.
- **Tanpa encode ulang**: video dan audio hanya digabung (*remux*) ke MP4, jadi kualitasnya sama persis dengan yang ada di server YouTube.
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

python download.py "https://youtu.be/VIDEO_ID"            # video kualitas tertinggi
python download.py URL -q 1080                            # maksimal 1080p
python download.py URL --compatible                       # H.264 + AAC, bisa diputar di mana saja
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
| Kualitas gambar dan suara maksimal | *(default)* | AV1/VP9 + Opus dalam MP4, resolusi tertinggi |
| Diputar di QuickTime, iPhone, WhatsApp, TV lama | `--compatible` | H.264 + AAC dalam MP4, biasanya maksimal 1080p |
| Audio kualitas maksimal | `--audio` | Opus asli (`.opus`) |
| Audio untuk iPhone/Apple Music | `--audio --compatible` | AAC asli (`.m4a`), tanpa konversi |
| Audio untuk perangkat lama | `--audio-format mp3` | MP3 VBR kualitas tertinggi (~245 kbps) |

File mode default berisi codec AV1/VP9 + Opus, yang paling bagus kualitasnya tetapi belum didukung semua pemutar. Buka dengan [IINA](https://iina.io/) atau [VLC](https://www.videolan.org/) di Mac. Jika file harus bisa dibuka di QuickTime atau dikirim ke HP, pakai `--compatible`.

Konversi audio ke MP3, FLAC, atau WAV tidak menambah kualitas karena sumbernya dari YouTube sudah terkompresi. Format `best` (default) adalah yang paling bagus.

## Jika download gagal

- Perbarui yt-dlp, karena YouTube sering mengubah sistemnya: `pip install -U -r requirements.txt`
- Untuk video yang dibatasi umur, khusus member, atau kualitas YouTube Premium, pakai login dari browser: `--cookies-from-browser chrome` (atau `safari`, `firefox`).

## Notebook lama

`main.ipynb` berisi percobaan awal (pytube dan yt-dlp) sebelum dirapikan menjadi `download.py`. Sel pytube sudah tidak berfungsi, dan beberapa sel di sana meng-encode ulang video atau mengonversi audio ke MP3 192 kbps sehingga kualitasnya turun. Gunakan `download.py`.

## Catatan

Gunakan hanya untuk video yang Anda miliki haknya atau yang lisensinya mengizinkan untuk didownload, dan patuhi Ketentuan Layanan YouTube.
