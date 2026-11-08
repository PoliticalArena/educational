#!/usr/bin/env bash
# Build the reel's audio bed (music + SFX) and mix it under a voiceover.
# Usage: tools/sound_design.sh <voiceover.mp3> <out.m4a>
# Cue times match reels/hyderabad-university-casteism/spec.json.
set -euo pipefail
VO="$1"; OUT="$2"; D=32
# Pass "none" as the voiceover to get a music + SFX bed only (for recording your own voice over it).
if [ "$VO" = "none" ]; then VO_IN=(-f lavfi -i "anullsrc=r=44100:cl=mono:d=$D"); else VO_IN=(-i "$VO"); fi

ffmpeg -y -loglevel error "${VO_IN[@]}" \
  -f lavfi -i "aevalsrc='0.35*sin(2*PI*55*t)+0.25*sin(2*PI*82.41*t)+0.12*sin(2*PI*110.3*t)':s=44100:d=$D" \
  -f lavfi -i "anoisesrc=color=brown:amplitude=0.6:d=$D:r=44100" \
  -f lavfi -i "aevalsrc='0.9*sin(2*PI*52*mod(t,0.70588))*exp(-14*mod(t,0.70588))':s=44100:d=$D" \
  -f lavfi -i "anoisesrc=color=white:amplitude=0.8:d=0.7:r=44100" \
  -f lavfi -i "aevalsrc='0.9*sin(2*PI*(120-80*min(t/1.2,1))*t)*exp(-2.2*t)':s=44100:d=1.6" \
  -f lavfi -i "aevalsrc='(sin(2*PI*58*t)*exp(-6*t)+0.3*random(0)*exp(-30*t))':s=44100:d=1.5" \
  -f lavfi -i "aevalsrc='0.6*random(0)*lt(mod(t,0.093),0.004)':s=44100:d=1.8" \
  -filter_complex "
    [1]tremolo=f=0.25:d=0.5,volume=0.5[drone];
    [2]lowpass=f=320,volume=0.35[rumble];
    [3]lowpass=f=140,volume=0.45[pulse];
    [drone][rumble][pulse]amix=inputs=3:normalize=0,afade=t=in:d=0.4,afade=t=out:st=30.2:d=1.8,volume=0.18*2.2[music];
    [4]bandpass=f=1800:w=2500,afade=t=in:d=0.25,afade=t=out:st=0.25:d=0.45,volume=0.55,asplit=3[w1][w2][w3];
    [w1]adelay=0|0[wh0];
    [w2]adelay=18800|18800[wh19];
    [w3]adelay=26800|26800[wh27];
    [5]volume=0.9,adelay=17100|17100[drop];
    [6]lowpass=f=400,volume=1.0,adelay=23400|23400[drum];
    [7]highpass=f=2000,volume=0.5,adelay=9600|9600[typing];
    [wh0][wh19][wh27][drop][drum][typing]amix=inputs=6:normalize=0:duration=longest,apad=whole_dur=$D[sfx];
    [0]aformat=channel_layouts=mono,aresample=44100,apad=whole_dur=$D,volume=1.0,asplit=2[vo][vokey];
    [music][vokey]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[ducked];
    [vo][ducked][sfx]amix=inputs=3:normalize=0:duration=longest,atrim=0:$D,alimiter=limit=0.95,aformat=channel_layouts=stereo[out]" \
  -map "[out]" -c:a aac -b:a 192k "$OUT"
echo "wrote $OUT"
