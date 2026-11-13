#!/usr/bin/env python3
"""Tighten a talking-head recording to a target length with jump cuts.

Detects pauses with ffmpeg's silencedetect, shrinks every pause to a short
breath, and alternates a subtle punch-in zoom at each visible cut so the
jumps read as deliberate edits. iPhone HLG/Dolby Vision footage is
tone-mapped to SDR BT.709 so it doesn't look washed out on social apps.

Usage:
  python3 tools/tighten_cut.py IN.MOV OUT.mp4 [--target 178] [--audio-stream 0:2]
      [--noise -38] [--zoom 1.10] [--face-y 0.62] [--dry-run]

The pause kept between phrases (--keep) is lowered automatically until the
cut fits under --target seconds (never below --min-keep).
"""
import argparse
import json
import re
import subprocess
import sys


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=index,codec_type,codec_name,color_transfer,r_frame_rate",
         "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def detect_silences(path, audio_map, noise_db, min_dur):
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", audio_map,
           "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends))


def keep_segments(silences, duration, keep):
    """Speech spans padded by keep/2 on each side; pauses collapse to `keep`."""
    half = keep / 2
    segs, cur = [], 0.0
    for s, e in silences:
        if s <= 0.05:            # leading silence: start just before speech
            cur = max(0.0, e - half)
            continue
        if e >= duration - 0.05:  # trailing silence: end just after speech
            segs.append((cur, min(duration, s + half)))
            cur = None
            break
        segs.append((cur, s + half))
        cur = e - half
    if cur is not None:
        segs.append((cur, duration))
    return [(a, b) for a, b in segs if b - a > 0.05]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--target", type=float, default=178.0, help="max output seconds")
    ap.add_argument("--audio-stream", default=None, help="ffmpeg map for the AAC track, e.g. 0:2")
    ap.add_argument("--noise", type=float, default=-38.0)
    ap.add_argument("--min-pause", type=float, default=0.3)
    ap.add_argument("--keep", type=float, default=0.30)
    ap.add_argument("--min-keep", type=float, default=0.16)
    ap.add_argument("--zoom", type=float, default=1.10)
    ap.add_argument("--face-y", type=float, default=0.62, help="zoom centre, fraction of height")
    ap.add_argument("--jump-threshold", type=float, default=0.25,
                    help="only toggle zoom at cuts removing at least this many seconds")
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    info = probe(a.src)
    duration = float(info["format"]["duration"])
    streams = info["streams"]
    if a.audio_stream is None:
        aac = [s for s in streams if s["codec_type"] == "audio" and s.get("codec_name") == "aac"]
        aud = aac[0] if aac else next(s for s in streams if s["codec_type"] == "audio")
        a.audio_stream = f"0:{aud['index']}"
    vid = next(s for s in streams if s["codec_type"] == "video")
    hdr = vid.get("color_transfer") in ("arib-std-b67", "smpte2084")
    num, den = map(int, vid["r_frame_rate"].split("/"))
    fps = num / den

    silences = detect_silences(a.src, a.audio_stream, a.noise, a.min_pause)
    keep = a.keep
    while True:
        segs = keep_segments(silences, duration, keep)
        total = sum(b - a_ for a_, b in segs)
        if total <= a.target or keep <= a.min_keep:
            break
        keep = round(keep - 0.02, 3)
    print(f"source {duration:.2f}s, {len(silences)} pauses, keep={keep:.2f}s "
          f"-> {len(segs)} segments, {total:.2f}s", file=sys.stderr)
    if total > a.target:
        print(f"WARNING: still {total:.2f}s > target {a.target}s; trim content manually.",
              file=sys.stderr)

    # Snap cuts to the frame grid so audio and video keep identical lengths
    # (otherwise per-cut rounding accumulates into visible lip-sync drift).
    segs = [(round(s * fps) / fps, round(e * fps) / fps) for s, e in segs]
    segs = [(s, e) for s, e in segs if e > s]
    total = sum(e - s for s, e in segs)
    h = 0.5 / fps
    vsel = "+".join(f"between(t,{s - h:.5f},{e - h:.5f})" for s, e in segs)
    asel = "+".join(f"gte(t,{s:.5f})*lt(t,{e:.5f})" for s, e in segs)
    # Zoom state per segment: toggle only where the removed gap is visible.
    zoomed, state = [], False
    for i, (s, e) in enumerate(segs):
        if i > 0 and s - segs[i - 1][1] >= a.jump_threshold:
            state = not state
        zoomed.append(state)

    # Output-frame boundaries where zoom is on.
    zranges, t_out = [], 0.0
    for (s, e), z in zip(segs, zoomed):
        f0, f1 = round(t_out * fps), round((t_out + e - s) * fps)
        if z:
            zranges.append(f"between(on,{f0},{f1 - 1})")
        t_out += e - s
    zexpr = f"if({'+'.join(zranges) or '0'},{a.zoom},1)"

    tonemap = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,"
               "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,") if hdr else "format=yuv420p,"
    vf = (f"[0:v:0]select='{vsel}',setpts=N/FRAME_RATE/TB,{tonemap}"
          f"zoompan=z='{zexpr}':d=1:fps={fps:g}:s=1080x1920:"
          f"x='iw/2-iw/zoom/2':y='min(max(ih*{a.face_y}-ih/zoom/2,0),ih-ih/zoom)',"
          f"setsar=1[v];"
          f"[{a.audio_stream}]asetnsamples=n=48:p=0,aselect='{asel}',asetpts=N/SR/TB,"
          f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    script = a.dst + ".filter.txt"
    with open(script, "w") as fh:
        fh.write(vf)
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", a.src, "-filter_complex_script", script,
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
           "-crf", str(a.crf), "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", a.dst]
    with open(a.dst + ".cuts.json", "w") as fh:
        json.dump({"source": a.src, "keep_pause_s": keep, "output_s": round(total, 2),
                   "segments": [[round(s, 3), round(e, 3), z] for (s, e), z in zip(segs, zoomed)]},
                  fh, indent=1)
    print(" ".join(cmd), file=sys.stderr)
    if not a.dry_run:
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
