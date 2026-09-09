#!/usr/bin/env python3
"""Bake masking noise into the track at fixed levels, for iOS.

On iOS any use of Web Audio suspends when the page backgrounds, so the live
pink-noise generator in the player costs you background playback. These
pre-mixed variants let the masking slider work with no audio graph at all:
the player just swaps the source file, and playback stays on the plain
media-element path that keeps running with the screen locked.

Variants are sample-aligned with the clean master, so switching mid-play can
preserve position exactly. The noise is wrapped onto itself the same way the
music is, so every variant still loops seamlessly.
"""
import numpy as np, wave, subprocess, sys

SR = 44100
SRC = "focus_dorian_drift.wav"
LEVELS = [33, 66, 100]          # percent, as amplitude relative to the music
WRAP = 10.0

print("reading master...", flush=True)
w = wave.open(SRC); N = w.getnframes()
music = np.frombuffer(w.readframes(N), '<i2').astype(np.float32).reshape(-1, 2) / 32768.0
w.close()
music_rms = float(np.sqrt((music ** 2).mean()))
print(f"  {N/SR/60:.2f} min, music rms {20*np.log10(music_rms):.1f} dBFS")


def moving_avg(x, win):
    win = int(win); pad = win // 2
    xd = x.astype(np.float64)
    xp = np.concatenate([np.full(pad, xd[0]), xd, np.full(win - pad, xd[-1])])
    c = np.cumsum(xp)
    return ((c[win:] - c[:-win]) / win)[:len(x)].astype(np.float32)


def pink(n, rng, octaves=16):
    """Voss-McCartney: sum of white sources updated at octave-spaced rates.
    Vectorised -- the IIR formulations need a per-sample Python loop, which is
    hopeless over 67M samples."""
    out = np.zeros(n, dtype=np.float32)
    for k in range(octaves):
        step = 1 << k
        vals = rng.standard_normal(n // step + 2).astype(np.float32)
        out += np.repeat(vals, step)[:n]
    return out / np.sqrt(octaves)


rng = np.random.default_rng(20260909)
Wn = int(SR * WRAP)
print("generating pink noise...", flush=True)
raw = np.stack([pink(N + Wn, rng), pink(N + Wn, rng)])          # independent L/R

print("wrapping + shaping...", flush=True)
xf = (np.arange(Wn, dtype=np.float32) / Wn) * (np.pi / 2)
hd, tl = np.sin(xf), np.cos(xf)
noise = raw[:, :N].copy()
noise[:, :Wn] = raw[:, :Wn] * hd + raw[:, N:N + Wn] * tl        # loops onto itself
del raw
for c in range(2):
    noise[c] = moving_avg(noise[c], 8)                          # match the player's tilt
noise /= np.sqrt((noise ** 2).mean())                           # unit rms
noise = np.ascontiguousarray(noise.T)                           # (N,2) to match music

for pct in LEVELS:
    print(f"mixing {pct}%...", flush=True)
    mix = music + noise * np.float32(music_rms * pct / 100.0)
    mix = np.tanh(mix * np.float32(1.15)).astype(np.float32)
    mix *= np.float32(0.891 / np.abs(mix).max())                # -1 dBFS
    tmp = f"_mix{pct}.wav"
    with wave.open(tmp, 'wb') as o:
        o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR)
        o.writeframes((mix * 32767).astype('<i2').tobytes())
    out = f"focus_dorian_drift_n{pct}.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:a", "aac_at",
                    "-b:a", "128k", "-movflags", "+faststart", out], check=True)
    subprocess.run(["rm", "-f", tmp], check=True)
    print(f"  wrote {out}", flush=True)
print("done")
