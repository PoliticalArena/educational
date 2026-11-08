# Hyderabad University Casteism Controversy — Reel (9:16, 32s)

| File | Purpose |
|---|---|
| `spec.json` | **Production spec (v2)**. Use this one. |
| `spec.v1.original.json` | The original brief, kept for reference. |
| `captions.hi.srt` | Hindi voiceover captions generated from `spec.json`. |

Validate the spec and rebuild the captions:

```bash
python3 tools/validate_reel.py reels/hyderabad-university-casteism/spec.json \
  --srt reels/hyderabad-university-casteism/captions.hi.srt
```

## What changed from v1

1. **Timing.** At about 2.8 words/sec (Hindi news pace), the v1 voiceover ran about 40s against a 32s timeline:

   | Scene | Duration | v1 needs | v2 needs |
   |---|---|---|---|
   | 2 Context | 8s | 9.3s ❌ | 7.9s ✅ (tight) |
   | 4 Dept vs Student | 8s | 13.9s ❌ | 7.1s ✅ |
   | 5 CTA | 5s | 5.4s ❌ | 3.9s ✅ |

2. **Legal framing.** The reel names a real professor. The v1 hook stated the slur as fact. v2 starts with **आरोप**, labels the professor **आरोपी**, and uses the passive voice for the second quote ("ईमेल में ... कहा गया").
3. **No fake evidence.** The v1 prompts asked the AI to render an "authentic" email. v2 uses a blurred, generic UI. Composite the **sourced screenshot** on it if you have one, or put the quotes in as motion-graphic text in post.
4. **Retention.** The headline is on screen from frame 0, the cuts land on the key words, and the last frame loops back to scene 1.

## Pre-publish checklist

- [ ] Find a primary source for the email (screenshot, complaint copy or a credible outlet's report). Link it in the caption.
- [ ] Check that both quotes match the source **word for word**.
- [ ] Check names and designations: Prof. Vijay Ramdas Mandala (History, UoH) and Subodh Kumar (former student).
- [ ] Find a source for the department's "apology given, matter closed" position.
- [ ] If the professor or the university has responded publicly, add one line in scene 4.
- [ ] Turn on the platform's **AI-generated content** label (synthetic presenter).
- [ ] Keep all text inside the safe zone (220px top, 380px bottom).

## Repurposing

- **Carousel (IG/LinkedIn, 5 slides):** Hook quote → who/where → second quote → "Apology vs inquiry" → poll CTA.
- **X/Twitter thread:** One post per scene, with the source link in post 2.
- **YouTube Shorts:** Same cut. Title idea: `"Dalit Untouchable Idiot" — प्रोफेसर पर आरोप | Hyderabad University`.
- **Community post / poll:** "सिर्फ माफी या निष्पक्ष जांच?" with two options. It feeds comments back into the reel.

## Guide voiceover (timing only — not for publishing)

`audio/guide_track.mp3` is a robotic offline espeak-ng read, exactly 32s, with each line starting on its scene's start time. Drop it on the timeline to cut b-roll, then replace it with a human or ElevenLabs read.

```bash
python3 tools/guide_track.py reels/hyderabad-university-casteism/spec.json \
  reels/hyderabad-university-casteism/audio/guide_track.mp3
```

ElevenLabs flow with the finished scene 5 takes (voice: Maahir – Crime News Narrator):
https://elevenlabs.io/app/flows/abUpYmfJEdzC3uIpBKzX

## Video (rendered locally, no paid tools) — no voiceover

Record your own voice over these. Both are 1080×1920, 30fps, 32s, with music and SFX only. The music is left about 10 dB quieter than a finished mix so your voice sits on top.

| File | Use |
|---|---|
| `output/uoh_reel_no-voice_captions.mp4` | Hindi captions burned in. Read along with them so your timing matches. |
| `output/uoh_reel_no-voice_clean.mp4` | No captions. Add your own in CapCut/Premiere after recording. |
| `output/music_sfx_bed.m4a` | The audio bed on its own, if you want to mix it yourself. |

Line timings to hit while recording: 0–4s, 4–12s, 12–19s, 19–27s, 27–32s (the lines are in `captions.hi.srt`).

Rebuild:

```bash
SLUG=reels/hyderabad-university-casteism
node tools/render_reel.js $SLUG/video/composition.html /tmp/silent.mp4 32 30                    # with captions
HIDE_CAPTIONS=1 node tools/render_reel.js $SLUG/video/composition.html /tmp/silent_nocap.mp4 32 30
tools/sound_design.sh none /tmp/bed.m4a                                                         # music + SFX only
ffmpeg -y -i /tmp/silent.mp4 -i /tmp/bed.m4a -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k \
  -movflags +faststart -shortest $SLUG/output/uoh_reel_no-voice_captions.mp4
```

To mix your recorded voice in with ducking and -14 LUFS loudness, pass it instead of `none`: `tools/sound_design.sh my_voice.mp3 /tmp/mix.m4a`.
Preview any moment as a still: `node tools/render_reel.js $SLUG/video/composition.html --stills /tmp/stills 1.5 16 25.8`.
