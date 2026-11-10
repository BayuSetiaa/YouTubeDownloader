#!/usr/bin/env python3
"""Download video atau audio YouTube dengan kualitas terbaik memakai yt-dlp.

Secara default hasilnya langsung bisa diputar di QuickTime Player (macOS), iPhone, dan
iPad. Resolusi dan fps tertinggi dipilih lebih dulu, lalu pada resolusi itu diutamakan
codec H.264/HEVC + AAC supaya stream cukup disalin tanpa encode ulang. Jika resolusi
tertinggi hanya tersedia dalam AV1/VP9 (misal video 4K), video dikonversi ke HEVC dengan
bitrate tinggi. Pakai --original untuk menyimpan codec asli tanpa konversi sama sekali.

Judul, chapter, dan thumbnail ikut disisipkan ke dalam file.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import yt_dlp
    from yt_dlp.postprocessor import (
        EmbedThumbnailPP,
        FFmpegExtractAudioPP,
        FFmpegMetadataPP,
        FFmpegPostProcessor,
        PostProcessor,
    )
    from yt_dlp.utils import DownloadError, prepend_extension
except ImportError:
    sys.exit('yt-dlp belum terpasang. Jalankan: pip install -U -r requirements.txt')

DEFAULT_OUTPUT_DIR = 'downloads'
AUDIO_FORMATS = ('best', 'm4a', 'mp3', 'opus', 'flac', 'wav')
JS_RUNTIMES = ('deno', 'node', 'bun')
QUICKTIME_VIDEO_CODECS = {'h264', 'hevc'}
QUICKTIME_AUDIO_CODECS = {'aac', 'alac', 'mp3'}

EXAMPLES = """\
contoh:
  python download.py "https://youtu.be/VIDEO_ID"          video kualitas tertinggi, siap QuickTime
  python download.py URL -q 1080                          maksimal 1080p
  python download.py URL --original                       codec asli YouTube (untuk IINA/VLC)
  python download.py URL --audio                          audio saja, kualitas asli
  python download.py URL --audio-format mp3               audio saja dalam MP3
  python download.py URL1 URL2                            beberapa video sekaligus
  python download.py PLAYLIST_URL --playlist              satu playlist penuh
"""

CODEC_NAMES = (
    ('av01', 'AV1'), ('av1', 'AV1'), ('vp09', 'VP9'), ('vp9', 'VP9'), ('avc', 'H.264'),
    ('h264', 'H.264'), ('hev', 'H.265'), ('hvc', 'H.265'), ('h265', 'H.265'), ('opus', 'Opus'),
    ('mp4a', 'AAC'), ('aac', 'AAC'), ('vorbis', 'Vorbis'), ('mp3', 'MP3'), ('flac', 'FLAC'),
)


def codec_name(codec: str | None) -> str | None:
    if not codec or codec == 'none':
        return None
    lowered = codec.lower()
    return next((name for prefix, name in CODEC_NAMES if lowered.startswith(prefix)), codec)


class QuickTimePP(FFmpegPostProcessor):
    """Mengubah stream yang tidak didukung QuickTime: video menjadi HEVC, audio menjadi AAC."""

    @PostProcessor._restrict_to(images=False, audio=False)
    def run(self, info):
        path = info['filepath']
        streams = self.get_metadata_object(path)['streams']
        video = next((s for s in streams if s['codec_type'] == 'video'
                      and not s.get('disposition', {}).get('attached_pic')), None)
        audio = next((s for s in streams if s['codec_type'] == 'audio'), None)

        args = ['-map', '0', '-dn', '-ignore_unknown', '-c', 'copy']
        notes, reencode = [], False
        if video and video['codec_name'] == 'hevc' and video.get('codec_tag_string') != 'hvc1':
            args += ['-tag:v', 'hvc1']  # QuickTime hanya mengenali HEVC bertanda hvc1
            notes.append('tag HEVC → hvc1')
        elif video and video['codec_name'] not in QUICKTIME_VIDEO_CODECS:
            args += self._hevc_args(video)
            notes.append(f"video {codec_name(video['codec_name'])} → HEVC")
            reencode = True
        if audio and audio['codec_name'] not in QUICKTIME_AUDIO_CODECS:
            args += ['-c:a', 'aac', '-b:a', '256k']
            notes.append(f"audio {codec_name(audio['codec_name'])} → AAC 256 kbps")
        if not notes and info['ext'] == 'mp4':
            return [], info

        out_path = str(Path(path).with_suffix('.mp4'))
        temp_path = prepend_extension(out_path, 'temp')
        self.to_screen(f'Menyesuaikan agar bisa diputar di QuickTime: {", ".join(notes) or "MP4"}'
                       + (' (encode ulang, bisa memakan waktu)' if reencode else ''))
        self.run_ffmpeg(path, temp_path, args)
        Path(temp_path).replace(out_path)

        info['quicktime_notes'] = notes
        if out_path == path:
            return [], info
        info.update(filepath=out_path, ext='mp4')
        return [path], info  # file lama (bukan MP4) dihapus oleh yt-dlp

    @staticmethod
    def _hevc_args(video: dict) -> list[str]:
        ten_bit = '10' in video.get('pix_fmt', '')
        if sys.platform == 'darwin':
            # Encoder hardware Mac dengan kualitas konstan 75: pada pengujian skor VMAF ~98
            # dibanding sumber AV1 (>= 95 berarti perbedaannya tidak terlihat mata).
            args = ['-c:v', 'hevc_videotoolbox', '-allow_sw', '1', '-q:v', '75']
            if ten_bit:
                args += ['-profile:v', 'main10', '-pix_fmt', 'p010le']
        else:
            args = ['-c:v', 'libx265', '-crf', '18', '-preset', 'medium']
            if ten_bit:
                args += ['-pix_fmt', 'yuv420p10le']
        return [*args, '-tag:v', 'hvc1']


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
        print(f'  Sumber  : {" + ".join(quality) or "?"}')
        if notes := info.get('quicktime_notes'):
            print(f'  Konversi: {", ".join(notes)}')
        print(f'  File    : {path} ({size})\n')
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
        '--original', action='store_true',
        help='simpan codec asli YouTube (AV1/VP9 + Opus, termasuk HDR) tanpa konversi. '
             'Tidak bisa diputar di QuickTime; buka dengan IINA atau VLC')
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
        args.audio_format = 'best'
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
        'writethumbnail': args.audio_format != 'wav',  # WAV tidak mendukung cover art
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

    if args.audio:
        opts['format'] = 'bestaudio/best'
        if args.audio_format == 'm4a':
            # Ambil stream AAC asli supaya cukup disalin, tidak di-encode ulang dari Opus.
            opts['format_sort'] = ['acodec:aac']
        return opts

    opts['format'] = 'bestvideo*+bestaudio/best'
    opts['merge_output_format'] = 'mp4'  # digabung tanpa encode ulang
    res = f'res:{args.max_height}' if args.max_height else 'res'
    if not args.original:
        # Resolusi dan fps tertinggi dulu. Pada resolusi itu utamakan H.264/HEVC + AAC yang bisa
        # diputar QuickTime apa adanya; AV1/VP9 hanya dipakai (lalu dikonversi) jika resolusi
        # tertinggi tidak tersedia dalam H.264/HEVC.
        opts['format_sort'] = ['lang', res, 'fps', 'vcodec:h265', 'acodec:aac']
    elif args.max_height:
        # Urutan bawaan yt-dlp sudah memilih kualitas tertinggi: resolusi, fps, HDR, codec
        # terbaik (AV1/VP9), lalu bitrate.
        opts['format_sort'] = [res]
    return opts


def add_postprocessors(ydl: yt_dlp.YoutubeDL, args: argparse.Namespace) -> None:
    # Urutan penting: konversi QuickTime dijalankan setelah metadata ditulis (supaya tag hvc1
    # tidak hilang), dan thumbnail disisipkan paling akhir.
    if args.audio:
        # preferredquality 0 = VBR tertinggi; diabaikan jika audio cukup disalin tanpa konversi.
        ydl.add_post_processor(FFmpegExtractAudioPP(
            ydl, preferredcodec=args.audio_format, preferredquality='0'))
    ydl.add_post_processor(FFmpegMetadataPP(ydl, add_metadata=True, add_chapters=True))
    if not args.audio and not args.original:
        ydl.add_post_processor(QuickTimePP(ydl))
    if args.audio_format != 'wav':
        ydl.add_post_processor(EmbedThumbnailPP(ydl, already_have_thumbnail=False))
    ydl.add_post_processor(SummaryPP(ydl), when='after_move')


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
            add_postprocessors(ydl, args)
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
