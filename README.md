# YouTubeDownloader

Kumpulan contoh kode Python untuk mendownload video dan audio dari YouTube, ditulis dalam notebook Jupyter (`main.ipynb`).

## Isi notebook

| Sel | Library | Fungsi |
|---|---|---|
| 0–2 | `pytube` | Percobaan awal: download resolusi tertinggi |
| 3–4 | `yt-dlp` | Download kualitas `best` |
| 5–7 | `yt-dlp` | Video maksimal 1080p, dikonversi ke MP4 |
| 8 | `yt-dlp` | Video + audio terbaik, digabung jadi MP4 |
| 9 | `yt-dlp` | Audio saja, dikonversi ke MP3 192 kbps |
| 10 | `yt-dlp` | Video maksimal 480p, digabung jadi MP4 |

> `pytube` sudah tidak aktif dikembangkan dan sering gagal (HTTP 403). Gunakan sel yang memakai `yt-dlp`.

## Cara menjalankan

1. Pasang [FFmpeg](https://ffmpeg.org/) (dibutuhkan untuk menggabungkan video/audio dan konversi ke MP3). Di macOS:
   ```bash
   brew install ffmpeg
   ```
2. Buat virtual environment dan pasang dependensi:
   ```bash
   python3 -m venv env
   source env/bin/activate
   pip install -U -r requirements.txt jupyter
   ```
3. Buka notebook, ganti nilai `video_url` dengan link YouTube yang ingin didownload, lalu jalankan selnya:
   ```bash
   jupyter notebook main.ipynb
   ```

Jika download gagal, perbarui `yt-dlp` terlebih dahulu (`pip install -U yt-dlp`), karena YouTube sering mengubah sistemnya.

## Catatan

Gunakan hanya untuk video yang Anda miliki haknya atau yang lisensinya mengizinkan untuk didownload, dan patuhi Ketentuan Layanan YouTube.
