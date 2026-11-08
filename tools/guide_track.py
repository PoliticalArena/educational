#!/usr/bin/env python3
"""Render an offline, robotic Hindi *guide* voiceover from a reel spec.

Each scene's line is synthesised with espeak-ng, sped up if it overruns its
slot, then padded with silence so every line starts exactly on its scene's
start time. The result is a timing reference for editing, not a publishable VO.

Requires: espeak-ng, ffmpeg
Usage:   python3 tools/guide_track.py reels/<slug>/spec.json reels/<slug>/audio/guide_track.mp3
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_WPM = 165   # espeak-ng words per minute to start from
MAX_WPM = 260
HEADROOM = 0.25  # seconds of silence kept at the end of each slot


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    return float(out.strip())


def synth(text: str, wpm: int, out: Path) -> float:
    subprocess.run(["espeak-ng", "-v", "hi", "-s", str(wpm), "-w", str(out), text], check=True)
    return duration(out)


def main() -> int:
    spec_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        padded: list[Path] = []
        for s in spec["scenes"]:
            slot = s["duration_seconds"]
            raw = tmpdir / f"s{s['scene_id']}_raw.wav"
            wpm = BASE_WPM
            took = synth(s["voiceover"], wpm, raw)
            while took > slot - HEADROOM and wpm < MAX_WPM:
                wpm += 15
                took = synth(s["voiceover"], wpm, raw)

            fixed = tmpdir / f"s{s['scene_id']}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
                 "-af", f"apad,atrim=0:{slot}", "-ar", "44100", "-ac", "1", str(fixed)],
                check=True,
            )
            padded.append(fixed)
            flag = "OK" if took <= slot else "OVERRUN (trimmed)"
            print(f"scene {s['scene_id']}: {took:4.1f}s of {slot}s at {wpm} wpm  {flag}")

        listing = tmpdir / "list.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in padded))
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
             "-c:a", "libmp3lame", "-q:a", "4", str(out_path)],
            check=True,
        )
    print(f"wrote {out_path} ({duration(out_path):.2f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
