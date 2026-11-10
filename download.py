#!/usr/bin/env python3
"""Download video atau audio YouTube dengan kualitas terbaik memakai yt-dlp.

Secara default script ini mengambil stream video dan audio terbaik yang
tersedia (resolusi, fps, HDR, dan codec tertinggi), lalu menggabungkannya
tanpa encode ulang sehingga kualitasnya tetap sama persis dengan sumbernya.
Judul, chapter, dan thumbnail ikut disisipkan ke dalam file.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import yt_dlp
    from yt_dlp.postprocessor import PostProcessor
    from yt_dlp.utils import DownloadError
except ImportError:
    sys.exit('yt-dlp belum terpasang. Jalankan: pip install -U -r requirements.txt')

DEFAULT_OUTPUT_DIR = 'downloads'
AUDIO_FORMATS = ('best', 'm4a', 'mp3', 'opus', 'flac', 'wav')
JS_RUNTIMES = ('deno', 'node', 'bun')

EXAMPLES = """\
contoh:
  python download.py "https://youtu.be/VIDEO_ID"          video kualitas tertinggi
  python download.py URL -q 1080                          maksimal 1080p
  python download.py URL --compatible                     H.264 + AAC, bisa diputar di mana saja
  python download.py URL --audio                          audio saja, kualitas asli
  python download.py URL --audio-format mp3               audio saja dalam MP3
  python download.py URL1 URL2                            beberapa video sekaligus
  python download.py PLAYLIST_URL --playlist              satu playlist penuh
"""

CODEC_NAMES = (
    ('av01', 'AV1'), ('vp09', 'VP9'), ('vp9', 'VP9'), ('avc', 'H.264'), ('h264', 'H.264'),
    ('hev', 'H.265'), ('hvc', 'H.265'), ('h265', 'H.265'), ('opus', 'Opus'), ('mp4a', 'AAC'),
    ('aac', 'AAC'), ('vorbis', 'Vorbis'), ('mp3', 'MP3'), ('flac', 'FLAC'),
)


def codec_name(codec: str | None) -> str | None:
    if not codec or codec == 'none':
        return None
    lowered = codec.lower()
    return next((name for prefix, name in CODEC_NAMES if lowered.startswith(prefix)), codec)


class SummaryPP(PostProcessor):
    """Menampilkan ringkasan kualitas setelah setiap file selesai."""

    def run(self, info):
        path = Path(info['filepath'])
        size = f'{path.stat().st_size / 1_000_000:.1f} MB' if path.exists() else '?'

        quality = []
        if vcodec := codec_name(info.get('vcodec')):
            video = f"{info.get('height') or '?'}p"
            if info.get('fps'):
                video += f"{info['fps']:.0f}"
            if info.get('dynamic_range') not in (None, 'SDR'):
                video += f" {info['dynamic_range']}"
            quality.append(f'{video} {vcodec}')
        if acodec := codec_name(info.get('acodec')):
            audio = acodec
            if info.get('abr'):
                audio += f" {info['abr']:.0f} kbps"
            if (info.get('audio_channels') or 0) > 2:
                audio += f" {info['audio_channels']}ch"
            quality.append(audio)

        print(f'\n✔ {info.get("title", path.stem)}')
        print(f'  Sumber : {" + ".join(quality) or "?"}')
        print(f'  File   : {path} ({size})\n')
        return [], info


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Download video/audio YouTube dengan kualitas terbaik (yt-dlp).',
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('urls', nargs='+', metavar='URL', help='link video atau playlist YouTube')
    parser.add_argument('-a', '--audio', action='store_true', help='download audio saja')
    parser.add_argument(
        '--audio-format', choices=AUDIO_FORMATS,
        help='format audio (otomatis mengaktifkan --audio). "best" (default) = format asli tanpa '
             'konversi, kualitas paling tinggi. Format lain dikonversi dengan kualitas tertinggi; '
             'flac/wav tidak menambah kualitas, hanya berguna untuk editing')
    parser.add_argument(
        '-q', '--max-height', type=int, metavar='PIXEL',
        help='batas resolusi video, misal 2160, 1440, 1080, 720, 480 (default: tanpa batas)')
    parser.add_argument(
        '--compatible', action='store_true',
        help='pilih H.264 + AAC dalam MP4 supaya bisa diputar di QuickTime, iPhone, WhatsApp, '
             'atau TV lama. Biasanya maksimal 1080p dan tanpa HDR')
    parser.add_argument(
        '-o', '--output', default=DEFAULT_OUTPUT_DIR, metavar='FOLDER',
        help=f'folder hasil download (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument(
        '--playlist', action='store_true',
        help='download seluruh playlist jika link berisi playlist (default: hanya videonya)')
    parser.add_argument(
        '--cookies-from-browser', metavar='BROWSER',
        help='pakai login dari browser (chrome, safari, firefox, edge, brave) untuk video yang '
             'dibatasi umur, khusus member, atau kualitas Premium')

    args = parser.parse_args(argv)
    if args.max_height is not None and args.max_height <= 0:
        parser.error('--max-height harus angka positif, misal 1080')
    if args.audio_format:
        args.audio = True
    elif args.audio:
        # Dalam mode kompatibel, audio disimpan sebagai M4A (AAC) yang bisa diputar di mana saja.
        args.audio_format = 'm4a' if args.compatible else 'best'
    return args


def build_options(args: argparse.Namespace) -> dict:
    outtmpl = '%(title)s.%(ext)s'
    if args.playlist:
        outtmpl = '%(playlist_index&{:03d} - |)s' + outtmpl

    opts = {
        'paths': {'home': str(Path(args.output).expanduser())},
        'outtmpl': outtmpl,
        'noplaylist': not args.playlist,
        # Error tetap dilaporkan dan dihitung gagal, tetapi tidak menghentikan video lain di playlist.
        'ignoreerrors': True,
        # Format kualitas tertinggi sering berupa ratusan fragmen kecil; unduh beberapa sekaligus.
        'concurrent_fragment_downloads': 4,
        'writethumbnail': True,
        'postprocessors': [],
    }

    # Sejak akhir 2025 YouTube butuh JavaScript runtime agar semua format (termasuk kualitas
    # tertinggi) bisa diakses.
    if runtimes := {name: {} for name in JS_RUNTIMES if shutil.which(name)}:
        opts['js_runtimes'] = runtimes
    else:
        print('Peringatan: Deno tidak ditemukan, YouTube mungkin hanya memberi format terbatas. '
              'Pasang dengan: brew install deno', file=sys.stderr)

    if args.cookies_from_browser:
        opts['cookiesfrombrowser'] = (args.cookies_from_browser, None, None, None)

    postprocessors = opts['postprocessors']
    if args.audio:
        opts['format'] = 'bestaudio/best'
        if args.audio_format == 'm4a':
            # Ambil stream AAC asli supaya cukup disalin, tidak di-encode ulang dari Opus.
            opts['format_sort'] = ['acodec:aac']
        postprocessors.append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': args.audio_format,
            # 0 = kualitas VBR tertinggi. Diabaikan jika audio cukup disalin tanpa konversi.
            'preferredquality': '0',
        })
    else:
        opts['format'] = 'bestvideo*+bestaudio/best'
        opts['merge_output_format'] = 'mp4'  # digabung tanpa encode ulang
        # Urutan bawaan yt-dlp sudah memilih kualitas tertinggi: resolusi, fps, HDR, codec,
        # lalu bitrate. Di sini hanya ditambahkan batas resolusi atau preferensi codec.
        sort = [f'res:{args.max_height}'] if args.max_height else []
        if args.compatible:
            sort = ['vcodec:h264', *(sort or ['res']), 'acodec:aac']
        if sort:
            opts['format_sort'] = sort

    postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True, 'add_chapters': True})
    if args.audio_format == 'wav':
        opts['writethumbnail'] = False  # WAV tidak mendukung cover art
    else:
        postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})
    return opts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not shutil.which('ffmpeg'):
        print('FFmpeg tidak ditemukan. FFmpeg dibutuhkan untuk menggabungkan video dan audio '
              'kualitas tertinggi.\nPasang dengan: brew install ffmpeg', file=sys.stderr)
        return 1

    opts = build_options(args)
    failed = []
    for url in args.urls:
        # Satu instance per URL supaya status gagal dari URL sebelumnya tidak terbawa.
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.add_post_processor(SummaryPP(ydl), when='after_move')
            try:
                if ydl.download([url]) != 0:
                    failed.append(url)
            except DownloadError:
                failed.append(url)
            except KeyboardInterrupt:
                print('\nDibatalkan.', file=sys.stderr)
                return 130

    if failed:
        print(f'\n{len(failed)} link gagal didownload:', file=sys.stderr)
        for url in failed:
            print(f'  - {url}', file=sys.stderr)
        print('Tips: perbarui yt-dlp dengan  pip install -U -r requirements.txt  karena YouTube '
              'sering berubah. Untuk video yang butuh login, tambahkan  --cookies-from-browser chrome',
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
