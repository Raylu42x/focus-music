#!/usr/bin/env python3
"""
Deep-work focus bed generator. Pure numpy additive synthesis + convolution.

WHY IT SOUNDS LIKE THIS (the design constraints are all attention research):

 1. No lyrics, no speech-like material.
    Irrelevant speech disrupts verbal working memory (Salame & Baddeley 1982).
    Anything that parses as language competes with the phonological loop.

 2. Minimise "changing state".
    Jones' changing-state effect: sound that changes from segment to segment
    disrupts serial-order tasks far more than steady sound does. So: no beat,
    no groove, no repeating riff, no section boundaries. Chords glide rather
    than cut, over a 32s cycle, above a permanent D pedal.

 3. Keep the modulation spectrum away from 4-8 Hz.
    Speech energy modulates fastest around 4-5 Hz; the auditory system is
    tuned to it and it grabs attention. Every LFO here is 0.01-0.03 Hz
    (41s to 97s cycles) and even the bells average one event per ~5s.

 4. No sharp onsets.
    Fast transients trigger the orienting reflex. Bell attacks are 45 ms,
    pad attacks are effectively seconds long.

 5. Downward spectral tilt, nothing above ~9 kHz.
    High-frequency energy reads as arousing/alerting. A -6 dB/oct master
    tilt puts the perceived centre of mass low and "warm".

 6. Low crest factor / narrow dynamic range.
    A slow leveller keeps loudness constant so nothing ever pops out, and
    so the track works as a consistent acoustic mask at low playback level
    (target roughly 45-55 dBA, i.e. quieter than you think).

 7. No file-level fades: the player crossfades the loop, so there is never
    a track boundary or a silence to notice. Novelty is the enemy.
"""
import numpy as np, wave, sys

SR = 44100
PROGRESSION = 192.0          # 6 chords x 32 s
CYCLES = 8                   # -> 1536 s = 25.6 min
SECONDS = PROGRESSION * CYCLES
WRAP = 10.0                  # extra tail, folded back over the head to loop
N  = int(SR * SECONDS)       # length of the delivered file
NW = N + int(SR * WRAP)      # length actually rendered
rng = np.random.default_rng(1729)

def midi(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=np.float64) - 69.0) / 12.0)

t = np.arange(NW, dtype=np.float32) / SR
master = np.zeros((2, NW), dtype=np.float32)

def moving_avg(x, win):
    """O(n) centred moving average. np.convolve is O(n*win) and dies on a
    45-minute buffer with a multi-second window."""
    win = int(win)
    pad = win // 2
    xd = x.astype(np.float64)
    xp = np.concatenate([np.full(pad, xd[0]),          # edge-replicate, not zeros:
                         xd,                           # zero padding makes the ends
                         np.full(win - pad, xd[-1])])  # read quiet and get boosted
    c = np.cumsum(xp)
    out = (c[win:] - c[:-win]) / win
    return out[:len(x)].astype(np.float32)


def lfo(freq_hz, phase=0.0, lo=0.0, hi=1.0):
    v = np.sin(2 * np.pi * freq_hz * t + phase, dtype=np.float32)
    return (lo + (hi - lo) * (v * 0.5 + 0.5)).astype(np.float32)

def osc(freq, amp, pan=0.0, drift_hz=0.02, drift_cents=3.0):
    """One detuned, slowly drifting sine summed into the master bus.

    Phase is accumulated in float64 (float32 cumsum drifts audibly over
    45 minutes) but in 4M-sample chunks -- a full-length float64 cumsum is a
    ~950 MB temporary per oscillator and puts the machine into swap.
    """
    l = np.float32(np.sqrt(0.5 * (1.0 - pan)))
    r = np.float32(np.sqrt(0.5 * (1.0 + pan)))
    ph = rng.uniform(0, 6.28)          # running phase, carried across chunks
    dph = rng.uniform(0, 6.28)         # drift-LFO phase
    CH = 1 << 22
    for i in range(0, NW, CH):
        j = min(i + CH, NW)
        tt = t[i:j]
        det = 2.0 ** ((drift_cents * np.sin(2 * np.pi * drift_hz * tt + dph,
                                            dtype=np.float32)) / 1200.0)
        f = (freq[i:j] if isinstance(freq, np.ndarray) else freq) * det
        acc = np.cumsum(f, dtype=np.float64) * (2 * np.pi / SR) + ph
        ph = float(acc[-1]) % (2 * np.pi)
        sig = np.sin(acc).astype(np.float32)
        del acc
        sig *= (amp[i:j] if isinstance(amp, np.ndarray) else np.float32(amp))
        master[0, i:j] += sig * l
        master[1, i:j] += sig * r
        del sig, f, det


# ------------------------------------------------- tonic pedal (never moves)
print("pedal...", flush=True)
breath = lfo(1 / 41.0, lo=0.78, hi=1.0)
osc(midi(26), 0.16 * breath, 0.00, drift_hz=0.011, drift_cents=1.5)   # D1
# ONE oscillator per pedal pitch. Two equal-amplitude sines at the same
# nominal frequency, each drifting independently, sum to anywhere between 2x
# and ZERO as their relative phase wanders. That was the loudest pair in the
# mix and it swung the whole track 11 dB on a ~12 s cycle. Stereo width comes
# from the pad and the air bed instead; a pedal should be rock steady.
osc(midi(38), 0.185 * breath, 0.00, drift_hz=0.013, drift_cents=0.8)  # D2
osc(midi(45), 0.05 * lfo(1 / 67.0, lo=0.35, hi=1.0), 0.25)            # A2
del breath

# ------------------------------------------------------------------- pad
CHORDS = [[50, 57, 60, 64],   # Dm9
          [50, 57, 60, 65],   # Bbmaj7
          [48, 55, 60, 64],   # Fmaj9
          [48, 57, 60, 64],   # Am7
          [50, 57, 62, 65],   # Gm9
          [50, 55, 62, 64]]   # Dm11 / Csus2
CHORD_SECS, GLIDE = 32.0, 6.0

def voice_freq_track(vi):
    idx = np.arange(NW, dtype=np.float64) / (SR * CHORD_SECS)
    step = np.floor(idx).astype(np.int64); frac = idx - step
    notes = np.array([c[vi] for c in CHORDS], dtype=np.float64)
    cur, nxt = notes[step % len(CHORDS)], notes[(step + 1) % len(CHORDS)]
    g = np.clip((frac - (1.0 - GLIDE / CHORD_SECS)) / (GLIDE / CHORD_SECS), 0.0, 1.0)
    g = g * g * (3 - 2 * g)                       # smoothstep, no corner to hear
    m = cur + (nxt - cur) * g
    del idx, step, frac, cur, nxt, g
    return midi(m).astype(np.float32)

HARMS = [(1, 1.00), (2, 0.40), (3, 0.17), (4, 0.085), (5, 0.040), (6, 0.020),
         (8, 0.011), (10, 0.006), (12, 0.0035)]
bright  = lfo(1 / 53.0, lo=0.22, hi=1.0)
bright2 = lfo(1 / 89.0, phase=1.1, lo=0.10, hi=0.9)
pad_env = lfo(1 / 71.0, phase=2.3, lo=0.60, hi=1.0)

for vi in range(4):
    print(f"pad voice {vi+1}/4...", flush=True)
    f0 = voice_freq_track(vi)
    for det_cents, pan in ((-6.0, -0.62), (0.0, 0.0), (7.0, 0.62)):
        base = (f0 * (2.0 ** (det_cents / 1200.0))).astype(np.float32)
        for h, ha in HARMS:
            if h * float(base.max()) > 12000:     # ceiling: nothing alerting up top
                continue
            amp = 0.030 * ha * pad_env
            if h >= 3: amp = amp * bright
            if h >= 5: amp = amp * bright2
            osc(base * h, amp, pan=pan * min(1.0, 0.4 + 0.1 * h),
                drift_hz=0.012 + 0.006 * h, drift_cents=2.5)
        del base
    del f0
del bright, bright2, pad_env

# -------------------------------------------------------------- air / mask
# Steady broadband bed. This is the part that actually masks office chatter:
# it raises the noise floor so speech peaks stop being intelligible.
print("air bed...", flush=True)
brown = np.cumsum(rng.standard_normal(NW).astype(np.float32) * 0.02, dtype=np.float32)
brown -= moving_avg(brown, 2048)                                    # remove rumble
brown /= (np.abs(brown).max() + 1e-9)
white = moving_avg(rng.standard_normal(NW).astype(np.float32), 4)   # gentle top
white /= (np.abs(white).max() + 1e-9)
pinkish = (0.86 * brown + 0.14 * white).astype(np.float32)         # ~1/f overall
del white
air = pinkish * (0.045 * lfo(1 / 97.0, lo=0.45, hi=1.0))
master[0] += air
master[1] += np.roll(air, 311)                                      # Haas width
del brown, pinkish, air

# ------------------------------------------------------- slow level rider
# Runs on the continuous bed (pedal + pad + air) ONLY, before the bells are
# added. Riding a signal that already contains bells means the bell transients
# drive the gain, and the gaps between bells read as large dips -- an early
# version swung 12 dB that way. Bells go on top afterwards at a fixed level.
print("levelling...", flush=True)
win = SR * 12
mono = np.abs(master[0]) + np.abs(master[1])
env = moving_avg(mono, win)
del mono
env = np.maximum(env, np.float32(1e-4))
target = np.float32(np.median(env))
gain = (target / env) ** np.float32(0.85)               # 85% of the way to flat
gain = np.clip(gain, 0.55, 1.8).astype(np.float32)
master *= gain
del env, gain

# ------------------------------------------------------------------ bells
# D minor pentatonic only: consonant against every chord above, so a note can
# never surprise you. Random walk with small steps = no melody to follow.
print("bells...", flush=True)
SCALE = np.array([62, 65, 67, 69, 72, 74, 77, 79, 81])
BELL_PARTIALS = [(1.0, 1.00, 3.6), (2.0, 0.30, 2.0),
                 (3.01, 0.12, 1.2), (4.21, 0.05, 0.7),
                 (6.83, 0.022, 0.45)]

# Bells are set relative to the bed that now exists in `master`, not to a
# guessed constant. An earlier version used a fixed 0.075 and the strikes came
# out level-competitive with the whole bed: 1 s RMS swung 12 dB at ~0.18 Hz
# (the mean strike spacing), which is exactly the "goes loud then normal" that
# this music is supposed to never do.
BED_RMS = float(np.sqrt((master ** 2).mean()))
PARTIAL_SUM = sum(a for _, a, _ in BELL_PARTIALS)      # peak of a vel=1 strike
BELL_GAIN = BED_RMS * 0.45 / PARTIAL_SUM               # ~7 dB under the bed
print(f"  bed rms {20*np.log10(BED_RMS):.1f} dBFS -> bell gain {BELL_GAIN:.4f}")


def bell(start_s, note, vel, pan):
    n, s = int(5.0 * SR), int(start_s * SR)
    if s + n >= NW: return
    tt = np.arange(n, dtype=np.float32) / SR
    atk = np.clip(tt / 0.045, 0, 1).astype(np.float32) ** 2   # 45 ms soft onset
    f = float(midi(note)); out = np.zeros(n, dtype=np.float32)
    for ratio, a, decay in BELL_PARTIALS:
        if f * ratio > 12000: continue
        out += (a * np.exp(-tt / decay) *
                np.sin(2 * np.pi * f * ratio * tt + rng.uniform(0, 6.28))).astype(np.float32)
    out *= atk * np.float32(vel * BELL_GAIN)
    master[0, s:s + n] += out * np.float32(np.sqrt(0.5 * (1 - pan)))
    master[1, s:s + n] += out * np.float32(np.sqrt(0.5 * (1 + pan)))

pos, prev = 15.0, 4
while pos < SECONDS + WRAP - 8:
    prev = int(np.clip(prev + rng.integers(-2, 3), 0, len(SCALE) - 1))
    bell(pos, SCALE[prev], rng.uniform(0.40, 0.95), rng.uniform(-0.7, 0.7))
    gap = rng.uniform(7.0, 17.0)
    if rng.random() < 0.10: gap += rng.uniform(8, 20)    # let it breathe
    pos += gap

# ----------------------------------------------------------- convolutions
def ola_convolve(x, ir, block=1 << 18):
    m = len(ir)
    nfft = 1 << int(np.ceil(np.log2(block + m - 1)))
    IR = np.fft.rfft(ir, nfft)
    out = np.zeros(len(x) + m - 1, dtype=np.float32)
    for i in range(0, len(x), block):
        seg = x[i:i + block]
        y = np.fft.irfft(np.fft.rfft(seg, nfft) * IR, nfft)[:len(seg) + m - 1]
        out[i:i + len(y)] += y.astype(np.float32)
    return out[:len(x)]

def make_ir(seconds=4.5, seed=7):
    r = np.random.default_rng(seed)
    n = int(seconds * SR); tt = np.arange(n, dtype=np.float32) / SR
    ir = r.standard_normal(n).astype(np.float32) * np.exp(-tt * 1.4)
    ir = np.convolve(ir, np.ones(6, dtype=np.float32) / 6, mode='same')   # gently dark tail
    ir[:int(0.035 * SR)] = 0                                               # pre-delay
    return (ir / np.sqrt(np.sum(ir ** 2))).astype(np.float32)

def tilt_kernel(fc=4500.0):
    """One-pole lowpass as an FIR: gives the ~-6 dB/oct master tilt."""
    a = np.exp(-2 * np.pi * fc / SR)
    n = int(-8.0 / np.log(a))
    k = ((1 - a) * a ** np.arange(n)).astype(np.float32)
    return k / k.sum()

TILT = tilt_kernel()
for ch in range(2):                       # per channel: keeps peak RAM sane
    print(f"reverb + tilt ch{ch}...", flush=True)
    wet = ola_convolve(master[ch], make_ir(seed=7 + 6 * ch))
    master[ch] = master[ch] * np.float32(0.60) + wet * np.float32(0.55)
    del wet
    master[ch] = 0.78 * master[ch] + 0.22 * ola_convolve(master[ch], TILT)

master *= np.float32(0.85 / np.abs(master).max())
master = np.tanh(master * np.float32(1.2)).astype(np.float32)
master *= np.float32(0.891 / np.abs(master).max())      # -1 dBFS ceiling

crest = 20 * np.log10(np.abs(master).max() / np.sqrt((master ** 2).mean()))
print(f"crest factor: {crest:.1f} dB   duration: {SECONDS/60:.1f} min")

# Fold the extra WRAP seconds back over the opening with an equal-power
# crossfade. After this, sample N-1 is followed naturally by sample 0, so the
# file is a true loop: no seam to hide, and every segment join downstream is
# just a continuation.
print("wrapping loop...", flush=True)
Wn = int(SR * WRAP)
xf = (np.arange(Wn, dtype=np.float32) / Wn) * (np.pi / 2)
head, tail = np.sin(xf), np.cos(xf)
final = master[:, :N].copy()
final[:, :Wn] = master[:, :Wn] * head + master[:, N:N + Wn] * tail
master = final
del final

out = "/Users/bennett/Repos/Making Music/focus_dorian_drift.wav"
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((master.T * 32767).astype('<i2').tobytes())
print("wrote", out)
