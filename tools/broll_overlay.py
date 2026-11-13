#!/usr/bin/env python3
"""Add screenshot b-roll cards and burned-in captions to a cut video.

Usage:
  python3 tools/broll_overlay.py MASTER.mp4 REEL_DIR OUT.mp4 [--no-captions] [--crf 20]

REEL_DIR must hold:
  overlays.json  {trim_start, card_top, card_width, card_max_height,
                  overlays: [{image, crop:[x,y,w,h]|null, start, end, label?}]}
  captions.tsv   start<TAB>end<TAB>text   (times on MASTER's timeline; '#' lines ignored)

All times are on MASTER's timeline. trim_start drops dead air at the head,
and captions and cards are shifted to match.
"""
import argparse
import json
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
FONT_LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PAD = 40  # transparent margin around the card for the shadow


FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def text_image(text, width, size=50):
    """White panel with a large wrapped quote, for lines too small to read in a screenshot."""
    font = ImageFont.truetype(FONT_SERIF, size)
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=font) > width - 120 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    lh = int(size * 1.3)
    im = Image.new("RGB", (width, lh * len(lines) + 100), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 14, im.height), fill=(200, 30, 30))
    for i, line in enumerate(lines):
        d.text((60, 50 + i * lh), line, font=font, fill=(20, 20, 20))
    return im


def make_card(src, crop, width, max_h, label, out, text=None):
    im = text_image(text, width) if text else Image.open(src).convert("RGB")
    if crop:
        x, y, w, h = crop
        im = im.crop((x, y, x + w, y + h))
    inner_w = width - 16
    h = round(im.height * inner_w / im.width)
    im = im.resize((inner_w, h), Image.LANCZOS)
    label_h = 56 if label else 0
    if h + label_h + 16 > max_h:  # centre-crop vertically to fit
        keep = max_h - label_h - 16
        top = (h - keep) // 2
        im = im.crop((0, top, inner_w, top + keep))
        h = keep
    card_h = h + 16 + label_h
    card = Image.new("RGBA", (width, card_h), (255, 255, 255, 255))
    card.paste(im, (8, 8))
    if label:
        d = ImageDraw.Draw(card)
        font = ImageFont.truetype(FONT_LATIN, 30)
        d.rectangle((0, h + 16, width, card_h), fill=(17, 17, 17, 255))
        d.text((24, h + 16 + label_h // 2), label, font=font, fill=(255, 255, 255, 255), anchor="lm")
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, card_h - 1), radius=26, fill=255)
    card.putalpha(mask)
    canvas = Image.new("RGBA", (width + 2 * PAD, card_h + 2 * PAD), (0, 0, 0, 0))
    shadow = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle((PAD, PAD + 10, PAD + width, PAD + card_h + 10), radius=26, fill=150)
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    canvas.paste((0, 0, 0, 255), (0, 0), shadow)
    canvas.alpha_composite(card, (PAD, PAD))
    canvas.save(out)
    return canvas.size


def ass_time(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_ass(tsv, shift, out):
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Noto Sans Devanagari,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,70,70,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows = []
    for line in open(tsv, encoding="utf-8"):
        if not line.strip() or line.startswith("#"):
            continue
        s, e, text = line.rstrip("\n").split("\t", 2)
        rows.append((float(s) - shift, float(e) - shift, text))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(head)
        for i, (s, e, text) in enumerate(rows):
            # Hold each caption until the next one starts (up to 0.6s) so it doesn't flicker.
            if i + 1 < len(rows):
                e = min(max(e, rows[i + 1][0]), e + 0.6)
            fh.write(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{{\\fad(60,40)}}{text}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("master")
    ap.add_argument("reel_dir")
    ap.add_argument("out")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--crf", type=int, default=20)
    a = ap.parse_args()

    spec = json.load(open(os.path.join(a.reel_dir, "overlays.json")))
    shift = spec.get("trim_start", 0.0)
    tmp = tempfile.mkdtemp(prefix="broll_")

    inputs = ["-ss", f"{shift}", "-i", a.master]
    chain, last = [], "[0:v]"
    for i, o in enumerate(spec["overlays"]):
        png = os.path.join(tmp, f"card{i}.png")
        src = os.path.join(a.reel_dir, o["image"]) if o.get("image") else None
        cw, ch = make_card(src, o.get("crop"), spec["card_width"], spec["card_max_height"],
                           o.get("label"), png, text=o.get("text"))
        s, e = o["start"] - shift, o["end"] - shift
        dur = e - s
        inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", png]
        n = i + 1
        chain.append(
            f"[{n}:v]format=rgba,fade=t=in:st=0:d=0.18:alpha=1,"
            f"fade=t=out:st={dur - 0.18:.3f}:d=0.18:alpha=1,setpts=PTS-STARTPTS+{s:.3f}/TB[c{n}]")
        y0 = spec["card_top"] - PAD
        # Slide up 40px while fading in.
        chain.append(
            f"{last}[c{n}]overlay=x=(W-w)/2:y='{y0}+40*max(0\\,1-(t-{s:.3f})/0.25)':"
            f"eof_action=pass:enable='between(t,{s:.3f},{e:.3f})'[v{n}]")
        last = f"[v{n}]"
    if not a.no_captions:
        ass = os.path.join(tmp, "captions.ass")
        write_ass(os.path.join(a.reel_dir, "captions.tsv"), shift, ass)
        chain.append(f"{last}ass={ass}[vout]")
    else:
        chain.append(f"{last}null[vout]")
    script = os.path.join(tmp, "graph.txt")
    open(script, "w").write(";\n".join(chain))
    cmd = ["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex_script", script,
           "-map", "[vout]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium",
           "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", a.out]
    print("cards + graph in", tmp)
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
