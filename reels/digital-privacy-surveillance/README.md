# Digital Privacy & Surveillance — talking head (9:16, 2:58)

Source: `IMG_5770.MOV` (iPhone, 1080×1920, HLG/Dolby Vision HDR, **3:27**).

| File | What it is |
|---|---|
| `output/privacy_talk_final_captions_broll.mp4` | **Publish this one.** 2:58: ABP cold open, Hindi captions, b-roll cards and clips |
| `output/privacy_talk_2m58s.mp4` | The clean cut, with no captions or cards. 1080×1920, 30fps, H.264 SDR (BT.709), AAC 192k, about -14 LUFS. **2:58** |
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

| Cut time | Line | On screen |
|---|---|---|
| 2.4–8.5s | Hook | Banner: "क्या आपका फ़ोन सुरक्षित है?" / "Israeli tool + सरकार की मंजूरी" |
| 17.0–23.8s | राहुल गांधी ने video जारी किया | **Full-screen cutaway** to his phone-tapping video (`broll/rahul_gandhi_phone_video.mp4`) |
| 49–58s | Israeli software | Cellebrite headline |
| 58–61s | Israel से भारत सरकार | "India bypasses own rules" |
| 61–65s | विशेष मंजूरी | Quote: para 1, "exempted Cellebrite from procurement rules" |
| 65–73s | unlock in 5–7s | Police-with-phone photo |
| 73–82s | data निकाली जा सकती है | Quote: para 3, 100+ cloud services |
| 82–86s | Internet Freedom Foundation | IFF tweet, then the "Home Minister signed off" graphic |
| 86–88s | गृह मंत्री ने | Home Minister frame |
| 88–92s | NIA को छूट | Quote: para 2, waiver for 422 foreign forensic products |
| 92–99s | ध्रुव राठी ने दावा किया | Rathee photo (Getty credit) |
| 99–106s | phone cloning, दिल्ली पुलिस | "How did they get inside my phone?" |
| 158–173s | Closing question | Banner: "राष्ट्रीय सुरक्षा या निजता?" / "अपनी राय कमेंट में बताएं" |
| 173–178s | Subscribe | Banner: "Subscribe this channel" |

The hook and closing question follow the channel critique: a 0–2s Devanagari text hook and a polarising closing question. There is no channel branding; the end banner is a generic subscribe prompt.

Rebuild (after `tighten_cut.py`):

```bash
python3 tools/broll_overlay.py out.mp4 reels/digital-privacy-surveillance final.mp4
```

Captions need the Noto Sans Devanagari font (`apt-get install fonts-noto-core`).

## Cold open + assembly (v3)

The video now opens on 12s of the ABP News clip of Rahul Gandhi's phone-tapping allegation (`broll/abp_rahul_phone_tapping.mp4`). His pauses are tightened and the clip is cropped to the clean footage: the YouTube UI, subscribe button and headline strip are removed, and ABP's own watermark stays. There are no captions on it, and a "Credit: ABP News" tag runs for its full length. It leads straight into "क्या आपका phone सुरक्षित है?".

To stay under 3:00, one repetitive line was cut (master 36.78–46.44s: "जिसके तहत … source के द्वारा"). The sentence still reads "ऐसा कौन सा software है … निकाली जा रही है".

The DPDP / Puttaswamy section (about 2:06–2:26) now plays the RTI/DPDP news report (`broll/dpdp_rti_news.mp4`, muted) as a video card at the top of the frame.

**Source of truth:** edit `overlays.master.json` and `captions.master.tsv`, which are on the tighten_cut master's timeline. `overlays.json` and `captions.tsv` are generated.

```bash
python3 tools/tighten_cut.py IMG_5770.MOV out.mp4 --target 178.5          # 1. pause-tightened master
python3 tools/assemble_opener.py reels/digital-privacy-surveillance assemble.json master2.mp4   # 2. opener + line cut + re-timed spec
python3 tools/broll_overlay.py master2.mp4 reels/digital-privacy-surveillance final.mp4         # 3. cards, cutaways, captions
```
(`assemble.json` points `master` at the step-1 output. Change that path if you rebuild somewhere else.)

## Before publishing

- The ABP and Sansani Abtak clips are third-party news footage used for commentary. Keep them short and credited (the ABP handle is visible on screen, and the DPDP card is labelled).
- `broll/home_minister_frame.jpg` has another reel's text burned in. It is cropped out, but check that you have the rights to the frame.
- The Getty photo of Dhruv Rathee is used for news commentary and credited on the card.

## Not done yet

- **Content cuts.** The 2:58 length comes from pauses alone. To get to about 2:30, cut repeated lines by hand.
