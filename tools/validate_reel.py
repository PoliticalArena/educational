#!/usr/bin/env python3
"""Validate a reel spec JSON and optionally export Hindi/English captions as SRT.

Checks:
  * scene durations sum to total_duration_seconds
  * start/end timestamps (if present) are contiguous
  * voiceover fits the scene at the target speaking pace

Usage:
  python3 tools/validate_reel.py reels/<slug>/spec.json
  python3 tools/validate_reel.py reels/<slug>/spec.json --srt reels/<slug>/captions.srt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_WPS = 2.8  # Hindi news-read pace, words per second


def word_count(text: str) -> int:
    return len([w for w in re.split(r"[\s—\-–:,.।!?'\"]+", text) if w])


def srt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def validate(spec: dict) -> list[str]:
    errors: list[str] = []
    wps = spec.get("audio_settings", {}).get("target_pace_words_per_second", DEFAULT_WPS)
    scenes = spec["scenes"]

    total = sum(s["duration_seconds"] for s in scenes)
    if total != spec["total_duration_seconds"]:
        errors.append(f"durations sum to {total}s, expected {spec['total_duration_seconds']}s")

    cursor = 0.0
    print(f"{'#':<3}{'scene':<38}{'dur':>5}{'words':>7}{'needs':>7}  status")
    for s in scenes:
        if "start_seconds" in s:
            if s["start_seconds"] != cursor:
                errors.append(f"scene {s['scene_id']} starts at {s['start_seconds']}, expected {cursor}")
            if s["end_seconds"] - s["start_seconds"] != s["duration_seconds"]:
                errors.append(f"scene {s['scene_id']} start/end do not match duration")
        cursor += s["duration_seconds"]

        words = word_count(s["voiceover"])
        needed = words / wps
        ok = needed <= s["duration_seconds"]
        if not ok:
            errors.append(
                f"scene {s['scene_id']} voiceover needs ~{needed:.1f}s, has {s['duration_seconds']}s"
            )
        print(
            f"{s['scene_id']:<3}{s['name'][:36]:<38}{s['duration_seconds']:>4}s"
            f"{words:>7}{needed:>6.1f}s  {'OK' if ok else 'TOO LONG'}"
        )
    return errors


def write_srt(spec: dict, out: Path) -> None:
    lines: list[str] = []
    cursor = 0.0
    for i, s in enumerate(spec["scenes"], 1):
        start = s.get("start_seconds", cursor)
        end = s.get("end_seconds", cursor + s["duration_seconds"])
        cursor = end
        lines += [str(i), f"{srt_ts(start)} --> {srt_ts(end - 0.05)}", s["voiceover"], ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("--srt", type=Path, help="write voiceover captions to this .srt path")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    errors = validate(spec)
    if args.srt:
        write_srt(spec, args.srt)
    if errors:
        print("\nFAIL:\n  - " + "\n  - ".join(errors))
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
