#!/usr/bin/env python3
"""
Theater Audio Repair Tool
=========================
Downloads a media file from archive.org (or processes a local file) and
applies a multi-stage FFmpeg audio-correction pipeline designed to fix
common problems found in old, degraded, or poorly-recorded media:

  Stage 1 – High-pass filter        remove low-frequency rumble / hum  (≤ 80 Hz)
  Stage 2 – Low-pass filter         soften high-frequency tape hiss     (≥ 10 kHz)
  Stage 3 – Dynamic compressor      lift quiet passages, tame loud ones
  Stage 4 – Loudness normalization  EBU R128 broadcast-standard levels
  Stage 5 – Volume boost            optional extra amplification  (default +6 dB)

Requirements:
    FFmpeg must be installed and on your PATH.
    Download: https://ffmpeg.org/download.html

Usage:
    # Fix audio from an archive.org URL (downloads automatically)
    python audio_repair.py https://archive.org/details/pt-03-Monster-of-Mexico

    # Fix a local file
    python audio_repair.py my_movie.mp4

    # Extra boost for very quiet recordings
    python audio_repair.py my_movie.mp4 --boost 12

    # Choose output filename
    python audio_repair.py my_movie.mp4 --output fixed_movie.mp4

    # Audio-only output (strip video, produce a WAV)
    python audio_repair.py my_movie.mp4 --audio-only

    # Dry-run: show the FFmpeg command without running it
    python audio_repair.py my_movie.mp4 --dry-run
"""

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARCHIVE_METADATA_API = "https://archive.org/metadata/{identifier}"
ARCHIVE_DOWNLOAD_BASE = "https://archive.org/download/{identifier}/{filename}"

# Preferred media extensions – tried in this order when picking a file from
# an archive.org item that contains multiple formats.
PREFERRED_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".ogv", ".mpg", ".mpeg",
                        ".mp3", ".ogg", ".flac", ".wav", ".m4a"]

# ---------------------------------------------------------------------------
# FFmpeg helpers
# ---------------------------------------------------------------------------

def _require_ffmpeg() -> None:
    """Abort with a helpful message if FFmpeg is not found on PATH."""
    if shutil.which("ffmpeg") is None:
        sys.exit(
            "❌  FFmpeg not found on PATH.\n"
            "   Install it from https://ffmpeg.org/download.html\n"
            "   then re-run this tool."
        )


def _build_audio_filter(
    highpass_hz: int = 80,
    lowpass_hz: int = 10000,
    compressor_threshold: str = "-25dB",
    compressor_ratio: float = 4.0,
    compressor_attack: float = 5.0,
    compressor_release: float = 100.0,
    loudnorm_target: float = -16.0,
    loudnorm_tp: float = -1.5,
    loudnorm_lra: float = 11.0,
    boost_db: float = 6.0,
) -> str:
    """Return a single FFmpeg -af filter-chain string."""
    stages = [
        # Stage 1: remove low-frequency rumble / electrical hum
        f"highpass=f={highpass_hz}",
        # Stage 2: soften high-frequency tape hiss
        f"lowpass=f={lowpass_hz}",
        # Stage 3: dynamic compression – bring up quiet parts
        (
            f"acompressor="
            f"threshold={compressor_threshold}:"
            f"ratio={compressor_ratio}:"
            f"attack={compressor_attack}:"
            f"release={compressor_release}:"
            f"makeup=2dB"
        ),
        # Stage 4: EBU R128 loudness normalization
        (
            f"loudnorm="
            f"I={loudnorm_target}:"
            f"TP={loudnorm_tp}:"
            f"LRA={loudnorm_lra}"
        ),
        # Stage 5: explicit volume boost for very quiet recordings
        f"volume={boost_db:.1f}dB",
    ]
    return ", ".join(stages)


def _build_ffmpeg_cmd(
    input_path: str,
    output_path: str,
    audio_filter: str,
    audio_only: bool = False,
) -> list[str]:
    """Assemble the complete FFmpeg command list."""
    cmd = [
        "ffmpeg",
        "-y",                   # overwrite output without asking
        "-i", input_path,
    ]
    if audio_only:
        cmd += ["-vn"]          # drop video stream
    else:
        cmd += ["-c:v", "copy"] # copy video stream unchanged
    cmd += [
        "-af", audio_filter,
        "-c:a", "aac",          # re-encode audio with AAC for broad compatibility
        "-b:a", "192k",
        output_path,
    ]
    return cmd


# ---------------------------------------------------------------------------
# archive.org helpers
# ---------------------------------------------------------------------------

def _parse_identifier(url_or_id: str) -> str:
    """Extract the archive.org item identifier from a URL or return as-is."""
    parsed = urllib.parse.urlparse(url_or_id)
    if parsed.scheme in ("http", "https") and (
        parsed.netloc == "archive.org" or parsed.netloc.endswith(".archive.org")
    ):
        # /details/<identifier>  or  /download/<identifier>/...
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in ("details", "download"):
            return parts[1]
    return url_or_id  # treat raw string as identifier


def _get_archive_metadata(identifier: str) -> dict:
    """Fetch item metadata from the archive.org API."""
    url = ARCHIVE_METADATA_API.format(identifier=identifier)
    print(f"  📡  Fetching metadata for '{identifier}'…")
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "TheaterAudioRepair/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"❌  Could not fetch archive.org metadata: {exc}")


def _pick_best_file(files: list[dict]) -> dict | None:
    """Choose the best media file from an archive.org file list."""
    # Index by extension preference
    by_ext: dict[str, list[dict]] = {}
    for f in files:
        name = f.get("name", "")
        ext = Path(name).suffix.lower()
        by_ext.setdefault(ext, []).append(f)

    for ext in PREFERRED_EXTENSIONS:
        if ext in by_ext:
            candidates = by_ext[ext]
            # Prefer the largest file (best quality)
            candidates.sort(key=lambda f: int(f.get("size", 0) or 0), reverse=True)
            return candidates[0]
    return None


def _download_file(url: str, dest: Path) -> None:
    """Download *url* to *dest* with a progress indicator."""
    print(f"  ⬇️   Downloading: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "TheaterAudioRepair/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536
            with open(dest, "wb") as fh:
                while True:
                    buf = resp.read(chunk)
                    if not buf:
                        break
                    fh.write(buf)
                    downloaded += len(buf)
                    if total:
                        pct = downloaded * 100 // total
                        print(f"\r      {pct:3d}%  {downloaded // (1024*1024)} MB", end="", flush=True)
        print()  # newline after progress
    except Exception as exc:  # noqa: BLE001
        dest.unlink(missing_ok=True)
        sys.exit(f"❌  Download failed: {exc}")


# ---------------------------------------------------------------------------
# Core repair function
# ---------------------------------------------------------------------------

def repair(
    source: str,
    output: str | None = None,
    boost_db: float = 6.0,
    audio_only: bool = False,
    dry_run: bool = False,
    highpass_hz: int = 80,
    lowpass_hz: int = 10000,
) -> None:
    """
    Main entry point.

    *source* is either:
      - a local file path, or
      - an archive.org URL / item identifier.
    """
    _require_ffmpeg()

    # ------------------------------------------------------------------ #
    # 1. Resolve source → local file path
    # ------------------------------------------------------------------ #
    local_input: Path
    temp_download: Path | None = None

    parsed = urllib.parse.urlparse(source)
    is_remote = parsed.scheme in ("http", "https")

    if is_remote or (not os.path.exists(source)):
        # Treat as archive.org identifier / URL
        identifier = _parse_identifier(source)
        metadata = _get_archive_metadata(identifier)
        files = metadata.get("files", [])
        if not files:
            sys.exit(f"❌  No files found in archive.org item '{identifier}'.")

        best = _pick_best_file(files)
        if best is None:
            sys.exit(
                f"❌  Could not find a supported media file in '{identifier}'.\n"
                f"   Available files: {[f['name'] for f in files[:10]]}"
            )

        filename = best["name"]
        download_url = ARCHIVE_DOWNLOAD_BASE.format(
            identifier=identifier, filename=urllib.parse.quote(filename)
        )
        safe_suffix = secrets.token_hex(8)
        temp_dir = Path(tempfile.gettempdir())
        temp_download = temp_dir / f"theater_repair_{safe_suffix}_{Path(filename).name}"
        if not temp_download.exists():
            _download_file(download_url, temp_download)
        local_input = temp_download
    else:
        local_input = Path(source)
        if not local_input.exists():
            sys.exit(f"❌  File not found: {source}")

    # ------------------------------------------------------------------ #
    # 2. Determine output path
    # ------------------------------------------------------------------ #
    if output:
        out_path = Path(output)
    else:
        suffix = ".wav" if audio_only else local_input.suffix or ".mp4"
        stem = local_input.stem
        out_path = local_input.parent / f"{stem}_repaired{suffix}"

    # ------------------------------------------------------------------ #
    # 3. Build and run FFmpeg command
    # ------------------------------------------------------------------ #
    audio_filter = _build_audio_filter(
        highpass_hz=highpass_hz,
        lowpass_hz=lowpass_hz,
        boost_db=boost_db,
    )
    cmd = _build_ffmpeg_cmd(
        input_path=str(local_input),
        output_path=str(out_path),
        audio_filter=audio_filter,
        audio_only=audio_only,
    )

    print()
    print("  🔧  Audio repair pipeline:")
    print(f"      Stage 1 – High-pass filter      remove rumble ≤ {highpass_hz} Hz")
    print(f"      Stage 2 – Low-pass filter       soften hiss   ≥ {lowpass_hz} Hz")
    print( "      Stage 3 – Dynamic compressor    lift quiet passages")
    print( "      Stage 4 – Loudness normalize    EBU R128 (-16 LUFS)")
    print(f"      Stage 5 – Volume boost          +{boost_db:.0f} dB amplification")
    print()
    print(f"  📥  Input : {local_input}")
    print(f"  📤  Output: {out_path}")
    print()

    if dry_run:
        print("  🔍  Dry-run mode – FFmpeg command that would be executed:")
        print("      " + " ".join(cmd))
        return

    print("  ▶️   Running FFmpeg…\n")
    result = subprocess.run(cmd, check=False)  # noqa: S603

    if result.returncode != 0:
        sys.exit(f"\n❌  FFmpeg exited with code {result.returncode}.")

    size_mb = out_path.stat().st_size / (1024 * 1024) if out_path.exists() else 0
    print(f"\n  ✅  Done!  Repaired file: {out_path}  ({size_mb:.1f} MB)")

    if temp_download:
        print(f"\n  🗑️   Removing temporary download: {temp_download}")
        temp_download.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Theater Audio Repair – amplify and correct degraded recordings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python audio_repair.py https://archive.org/details/pt-03-Monster-of-Mexico\n"
            "  python audio_repair.py bad_audio.mp4 --boost 12\n"
            "  python audio_repair.py bad_audio.mp4 --output fixed.mp4\n"
            "  python audio_repair.py bad_audio.mp4 --audio-only\n"
            "  python audio_repair.py bad_audio.mp4 --dry-run\n"
        ),
    )
    parser.add_argument(
        "source",
        help="Local file path OR archive.org URL / item identifier",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: <input>_repaired.<ext>)",
    )
    parser.add_argument(
        "--boost", "-b",
        type=float,
        default=6.0,
        metavar="DB",
        help="Extra volume boost in dB applied after normalization (default: 6)",
    )
    parser.add_argument(
        "--highpass",
        type=int,
        default=80,
        metavar="HZ",
        help="High-pass cutoff in Hz — removes rumble below this frequency (default: 80)",
    )
    parser.add_argument(
        "--lowpass",
        type=int,
        default=10000,
        metavar="HZ",
        help="Low-pass cutoff in Hz — softens hiss above this frequency (default: 10000)",
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Strip video and output audio only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the FFmpeg command without executing it",
    )

    args = parser.parse_args()

    print("""
  ╔══════════════════════════════════════════════╗
  ║  🎙️  Theater Audio Repair Tool               ║
  ║  Amplify & correct degraded recordings       ║
  ╚══════════════════════════════════════════════╝
""")

    repair(
        source=args.source,
        output=args.output,
        boost_db=args.boost,
        audio_only=args.audio_only,
        dry_run=args.dry_run,
        highpass_hz=args.highpass,
        lowpass_hz=args.lowpass,
    )


if __name__ == "__main__":
    main()
