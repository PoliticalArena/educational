# Digital Privacy & Surveillance — talking head (9:16, 2:56)

Source: `IMG_5770.MOV` (iPhone, 1080×1920, HLG/Dolby Vision HDR, **3:27**).

| File | What it is |
|---|---|
| `output/privacy_talk_final_captions_broll.mp4` | **Publish this one.** 2:56: Hindi captions, screenshot b-roll cards, and the 2.2s of dead air at the start trimmed |
| `output/privacy_talk_2m58s.mp4` | The clean cut, with no captions or cards. | Final cut. 1080×1920, 30fps, H.264 SDR (BT.709), AAC 192k, about -14 LUFS. **2:58** |
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

## Captions + b-roll

- `captions.tsv` holds Hindi caption chunks timed from an ElevenLabs Scribe transcript of `audio/voice_cut.mp3`. The filler "जो है" is dropped, along with a few small grammar fixes.
- `overlays.json` lists each screenshot card, its crop and the spoken cue it lands on. The images are in `broll/`. One card is a quote card made from the article's third paragraph, because the screenshot text was too small to read on a phone.

| Cut time | Line | Card |
|---|---|---|
| 49–58s | Israeli software | Cellebrite headline |
| 58–65s | विशेष मंजूरी | "India bypasses own rules" |
| 65–73s | unlock in 5–7s | Police-with-phone photo |
| 73–82s | data निकाली जा सकती है | Quote: 100+ cloud services |
| 82–86s | Internet Freedom Foundation | IFF tweet, then the "Home Minister signed off" graphic |
| 86–91s | गृह मंत्री ने NIA को छूट | Home Minister frame |
| 91–99s | ध्रुव राठी ने दावा किया | Rathee photo (Getty credit) |
| 99–106s | phone cloning, दिल्ली पुलिस | "How did they get inside my phone?" |

Rebuild (after `tighten_cut.py`):

```bash
python3 tools/broll_overlay.py out.mp4 reels/digital-privacy-surveillance final.mp4
```

Captions need the Noto Sans Devanagari font (`apt-get install fonts-noto-core`).

## Before publishing

- Rahul Gandhi's video (around 15s) and the Puttaswamy / DPDP Act lines (around 128–145s) have no visuals. Add a clip or a headline there if you have one.
- `broll/home_minister_frame.jpg` has another reel's text burned in. It is cropped out, but check that you have the rights to the frame.
- The Getty photo of Dhruv Rathee is used for news commentary and credited on the card.

## Not done yet

- **Content cuts.** The 2:58 length comes from pauses alone. To get to about 2:30, cut repeated lines by hand.
