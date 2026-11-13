#!/usr/bin/env python3
"""Prepend a cold-open clip to a cut master, drop ranges from the master, and re-time the reel spec.

Usage:
  python3 tools/assemble_opener.py REEL_DIR assemble.json OUT_MASTER.mp4

assemble.json:
{
  "master": "path/to/out.mp4",           # the tighten_cut.py output
  "master_trim_start": 2.2,               # drop dead air at the master's head
  "remove": [[36.78, 46.44]],             # master-time ranges to cut
  "opener": {
    "clip": "broll/opener.mp4",
    "crop": [w, h, x, y],                 # region of the screen recording to keep
    "keep": [[1.65, 3.15], ...],          # opener-time segments to keep (pauses removed)
    "top": 100,                           # y of the clip on the 1080x1920 canvas
    "captions": [[1.76, 3.06, "text"], ...]  # opener-time captions (e.g. a translation)
  },
  "spec_in":  {"overlays": "overlays.master.json", "captions": "captions.master.tsv"},
  "spec_out": {"overlays": "overlays.json", "captions": "captions.tsv"}
}

The input spec is on the master's timeline. The output spec is on OUT_MASTER's
timeline (trim_start 0), so `tools/broll_overlay.py OUT_MASTER REEL_DIR final.mp4` renders it.
"""
import json
import os
import subprocess
import sys

FPS = 30


def snap(t):
    return round(t * FPS) / FPS


def main():
    reel, cfg_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    cfg = json.load(open(os.path.join(reel, cfg_path), encoding="utf-8"))
    op = cfg["opener"]
    keep = [(snap(a), snap(b)) for a, b in op["keep"]]
    L = sum(b - a for a, b in keep)

    t0 = cfg.get("master_trim_start", 0.0)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", cfg["master"]], capture_output=True, text=True)
    mdur = float(probe.stdout)
    removes = sorted((snap(a), snap(b)) for a, b in cfg.get("remove", []))
    body, cur = [], snap(t0)
    for a, b in removes:
        body.append((cur, a))
        cur = b
    body.append((cur, mdur))

    def remap(t):
        """master time -> new time, or None if it falls in a removed range."""
        if t < t0:
            return None
        acc = L
        for a, b in body:
            if t < a:
                return None
            if t <= b:
                return acc + (t - a)
            acc += b - a
        return None

    def opener_remap(t):
        acc = 0.0
        for a, b in keep:
            if t <= b:
                return acc + max(0.0, t - a)
            acc += b - a
        return acc

    # ---- render the new master ----
    # One seeked input per segment: trimming a single input into several branches makes
    # ffmpeg buffer everything the concat hasn't reached yet (runs out of memory).
    cw, ch, cx, cy = op["crop"]
    clip = os.path.join(reel, op["clip"])
    inputs, parts, labels, k = [], [], [], 0
    for i, (a, b) in enumerate(keep):
        inputs += ["-ss", f"{a:.4f}", "-t", f"{b - a:.4f}", "-i", clip]
        parts.append(f"[{k}:v]fps={FPS},crop={cw}:{ch}:{cx}:{cy},split[ob{i}][of{i}];"
                     f"[ob{i}]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                     f"gblur=sigma=40,eq=brightness=-0.2[obb{i}];"
                     f"[of{i}]scale=1080:-2[ofs{i}];"
                     f"[obb{i}][ofs{i}]overlay=0:{op.get('top', 100)},format=yuv420p,setsar=1,"
                     f"setpts=PTS-STARTPTS[ov{i}];"
                     f"[{k}:a]asetpts=PTS-STARTPTS,aresample=48000,"
                     f"afade=t=in:d=0.01,afade=t=out:st={b - a - 0.01:.4f}:d=0.01[oa{i}]")
        labels.append(f"[ov{i}][oa{i}]")
        k += 1
    parts.append(f"{''.join(labels)}concat=n={len(keep)}:v=1:a=1[opv][opa_raw];"
                 f"[opa_raw]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[opa]")
    blabels = []
    for i, (a, b) in enumerate(body):
        inputs += ["-ss", f"{a:.4f}", "-t", f"{b - a:.4f}", "-i", cfg["master"]]
        parts.append(f"[{k}:v]format=yuv420p,setsar=1,setpts=PTS-STARTPTS[bv{i}];"
                     f"[{k}:a]asetpts=PTS-STARTPTS,aresample=48000,"
                     f"afade=t=in:d=0.01,afade=t=out:st={b - a - 0.01:.4f}:d=0.01[ba{i}]")
        blabels.append(f"[bv{i}][ba{i}]")
        k += 1
    parts.append(f"[opv][opa]{''.join(blabels)}concat=n={len(body) + 1}:v=1:a=1[v][a]")
    graph = out + ".graph.txt"
    open(graph, "w").write(";\n".join(parts))
    cmd = ["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex_script", graph,
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
           "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-colorspace", "bt709", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)

    # ---- re-time the spec ----
    spec = json.load(open(os.path.join(reel, cfg["spec_in"]["overlays"]), encoding="utf-8"))
    new_ov = []
    for o in spec["overlays"]:
        s, e = remap(o["start"]), remap(o["end"])
        if s is None or e is None:
            print("dropped overlay (falls in a removed range):", o.get("cue"), file=sys.stderr)
            continue
        o = dict(o, start=round(s, 3), end=round(e, 3))
        new_ov.append(o)
    for o in cfg.get("extra_overlays", []):  # given on the master timeline
        o = dict(o, start=round(remap(o["start"]), 3), end=round(remap(o["end"]), 3))
        new_ov.append(o)
    new_ov.sort(key=lambda o: o["start"])
    spec["overlays"] = new_ov
    spec["trim_start"] = 0.0
    with open(os.path.join(reel, cfg["spec_out"]["overlays"]), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)

    lines = ["# start\tend\ttext   (generated by tools/assemble_opener.py; edit "
             + cfg["spec_in"]["captions"] + " instead)"]
    for s, e, text in op.get("captions", []):
        lines.append(f"{opener_remap(s):.2f}\t{opener_remap(e):.2f}\t{text}")
    for line in open(os.path.join(reel, cfg["spec_in"]["captions"]), encoding="utf-8"):
        if not line.strip() or line.startswith("#"):
            continue
        s, e, text = line.rstrip("\n").split("\t", 2)
        ns, ne = remap(float(s)), remap(float(e))
        if ns is None or ne is None:
            print("dropped caption:", text, file=sys.stderr)
            continue
        lines.append(f"{ns:.2f}\t{ne:.2f}\t{text}")
    with open(os.path.join(reel, cfg["spec_out"]["captions"]), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    total = L + sum(b - a for a, b in body)
    print(f"opener {L:.2f}s + body {total - L:.2f}s = {total:.2f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
