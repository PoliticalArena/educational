# Digital Privacy & Surveillance — talking head (9:16, 2:58)

Source: `IMG_5770.MOV` (iPhone, 1080×1920, HLG/Dolby Vision HDR, **3:27**).

| File | What it is |
|---|---|
| `output/privacy_talk_2m58s.mp4` | Final cut. 1080×1920, 30fps, H.264 SDR (BT.709), AAC 192k, about -14 LUFS. **2:58** |
| `output/cut_list.json` | Every kept segment (source in/out seconds, and whether it is zoomed in) |

## What was done

1. **Pauses tightened.** 72 pauses longer than 0.3s (below -38 dB) were each shortened to 0.22s. This took 29s out. No words were removed.
2. **Jump cuts hidden.** Each cut that removes 0.25s or more switches between a wide shot and a 1.10× punch-in centred on the face.
3. **HDR → SDR.** HLG was tone-mapped with Hable to BT.709, so it doesn't look washed out on Instagram, YouTube or WhatsApp.
4. **Loudness.** The audio is normalised to -14 LUFS with a -1.5 dBTP ceiling.
5. **Sync.** Cuts snap to the frame grid. Audio and video match to within about 2 frames.

## Rebuild

```bash
python3 tools/tighten_cut.py IMG_5770.MOV out.mp4 --target 178.5
```

`--target` sets the maximum length. The script lowers the kept pause until the cut fits.
Other options: `--zoom` (punch-in amount), `--face-y` (zoom centre), `--noise` (pause threshold), `--dry-run` (print the plan without rendering).

## Not done yet

- **Captions.** No speech-to-text model can be reached from this sandbox. Run the cut through CapCut auto-captions (Hindi), or Descript or OpusClip.
- **Content cuts.** The 2:58 length comes from pauses alone. To get to about 2:30, cut repeated lines by hand.
