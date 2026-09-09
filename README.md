# Deep Work — a generated focus bed

**Live: <https://focus.kervian.com>**

A 25:36 beatless ambient track, synthesised from scratch in numpy, plus a
player that loops it forever. No dependencies, no build step, no CDN, no
analytics, no accounts. The whole site is three static files and some audio.

Everything about the music is a deliberate attention-research constraint, and
every claim below was measured against the finished file rather than asserted —
see [Why it sounds like this](#why-it-sounds-like-this).

## Deployment

The site is served straight from the repository root by GitHub Pages — there is
no build step. `CNAME` points it at `focus.kervian.com`, and `.nojekyll` stops
Pages running the files through Jekyll.

To publish a change: commit and push to `main`.

DNS for the custom domain needs one record at the `kervian.com` registrar:

```
focus   CNAME   raylu42x.github.io.
```

then Settings → Pages → Custom domain → `focus.kervian.com`, and tick
*Enforce HTTPS* once the certificate has been issued (can take a few minutes).

## Run it locally

Double-click **`start.command`**. It serves this folder on localhost only and
opens the player. Close the window to stop. Space toggles play/pause.

To try it on a phone or iPad on the same wifi, double-click
**`share-on-wifi.command`** instead — it prints the URL to open on the device.

## Files

| file | what it is |
|---|---|
| `index.html` | desktop player — vanilla Web Audio, no libraries |
| `ios.html` | iPhone/iPad player — no AudioContext at all, ever |
| `style.css` | shared styling for both pages |
| `focus_dorian_drift.webm` | Opus 105 kbps, 20 MB — served where supported |
| `focus_dorian_drift.m4a` | AAC 129 kbps, 24 MB — fallback, covers every iPhone |
| `focus_dorian_drift_n{33,66,100}.m4a` | same track with masking noise pre-mixed, 24 MB each |
| `make_noise_variants.py` | generates those three |
| `focus_dorian_drift.flac` | lossless master, 129 MB — **local only, gitignored** |
| `focus_synth.py` | the synthesiser that generated it |
| `focus_dorian_drift.wav` | raw render, 258 MB — redundant, the FLAC matches it exactly |
| `serve.py` | localhost-only static server with HTTP Range support |
| `start.command` | double-click launcher (localhost) |
| `share-on-wifi.command` | double-click launcher that a phone on your wifi can reach |

Re-render with `python3 focus_synth.py` (~3 min), then encode both formats:

```
ffmpeg -y -i focus_dorian_drift.wav -c:a libopus -b:a 96k -vbr on \
       -application audio focus_dorian_drift.webm
ffmpeg -y -i focus_dorian_drift.wav -c:a aac_at -b:a 128k \
       -movflags +faststart focus_dorian_drift.m4a
```
Change `CYCLES` for length (keep it a whole number — see Looping below).
Change the `rng` seed near the top for a completely different piece.

## Why GitHub Pages is enough

Verified: Pages returns `206 Partial Content` for range
requests, so the browser streams progressively and only downloads what you
actually listen to. The 22 MB file is well under the 100 MB per-file hard limit
and the 1 GB repo soft limit. The bandwidth soft limit (100 GB/month) is about
4,500 full listens.

Use the VPS instead if you add more tracks, expect real traffic, or want long
`Cache-Control` headers — GitHub's terms discourage using Pages as a media CDN,
and one ambient loop on a personal site sits comfortably inside normal use but
a library of them does not.

Deploying is just copying `index.html` and `focus_dorian_drift.mp3` to the web
root. Nothing else is needed at runtime — `serve.py` and `start.command` are
local-development conveniences only.

### On splitting the file

Not needed, and it would make things worse. Range requests already give you the
"only fetch what you play" benefit without any extra machinery. Splitting adds a
real problem: MP3 carries encoder delay and end padding, so decoded segments do
not butt together sample-accurately, and joining them produces either a gap or —
if you overlap and crossfade — comb filtering, because the overlapping regions
are the same audio offset by a few milliseconds. The single file avoids all of
it. If the download ever does need to shrink, drop the bitrate or the length
rather than segmenting.

## The lossless master

`focus_dorian_drift.flac` is the archival copy: 25:36, 44.1 kHz/16-bit stereo,
bit-identical to what `focus_synth.py` renders (verified by MD5 against the raw
WAV before that WAV was deleted).

It is **not in the repository** — at 129 MB it exceeds GitHub's 100 MB per-file
hard limit — and nothing at runtime reads it. The website never touches it. Its
only job is to be the thing you re-encode *from*: going lossy-to-lossy (Opus out
of AAC, say) compounds artefacts, so any new bitrate or new noise variant should
start here.

`make_noise_variants.py` takes the WAV if one is lying around and otherwise
decodes this FLAC through ffmpeg. Because the noise seed is fixed, rebuilding
from the FLAC reproduces the WAV-sourced variants exactly — measured difference
between the two routes: **-240 dBFS**, i.e. the float32 noise floor.

If you lose it, `python3 focus_synth.py` regenerates the master from scratch.

## Formats

MP3 is gone. Two files are shipped and the player picks per browser with
`canPlayType`:

| | size | notes |
|---|---|---|
| **Opus / WebM** | 20 MB | best quality per byte; everything modern except old Safari |
| **AAC / MP4** | 24 MB | universal fallback — every iPhone, every Android |
| FLAC | 129 MB | lossless, local listening only, not served |

Besides being more efficient than MP3, both carry real gapless metadata (Opus
pre-skip, AAC edit lists). Measured across the loop point in-browser: Opus
dipped **0.0 dB**, AAC **0.5 dB**, with no silent samples in either. That is
what makes the next section possible.

## Phones

It works on a phone, with one honest caveat.

By default the page creates **no AudioContext at all** — it is a plain `<audio>`
element with `loop = true`. That matters: iOS suspends Web Audio graphs when the
page goes to the background, but plain media playback keeps running with the
screen locked and shows up in the lock-screen controls (MediaSession metadata is
set). The `output` row on the page reads `direct · background-safe`.

The moment you touch masking noise, warmth or the 40 Hz pulse, the page has to
build an audio graph, and that row flips to `processed · web audio`. On iPhone
you then get processing *or* background playback, not both. The page always
tells you which mode you are in.

### `ios.html` — the way around that

Rather than sniff the user agent, `index.html` just links to a separate iOS
build, and that page **never constructs an AudioContext** (verified by
instrumenting the constructor: zero built across a full session, including a
noise change).

Masking noise there is not generated live — it is four pre-mixed files at 0 /
33 / 66 / 100%, and the slider swaps between them. All four are sample-aligned
with the clean master (measured cross-correlation lag: **0 samples**) and sit
within 1 dB of each other in RMS, so switching carries your exact place in the
music across with no jump in level. It costs a short buffering pause, which is
why the page tells you to pick a level and leave it.

Warmth and the 40 Hz pulse need live processing, so they exist only in the
desktop build. The track is already mixed dark, so little is lost.

Volume on that page is the device's hardware buttons, because iOS does not let
a web page set playback volume at all.

The music slider is a special case: iOS ignores `HTMLMediaElement.volume`
entirely. The player feature-tests it (rather than sniffing the user agent) and
falls back to the graph only where it has to.

Two more iOS specifics:

- **A new AudioContext starts suspended on iOS.** Since routing the element
  through a suspended graph silences it outright, `ensureGraph()` resumes
  immediately (it runs inside the slider's user gesture), and any later tap
  re-resumes. Without this, touching a control on an iPhone killed the sound.
- **The hardware ringer switch mutes Web Audio but not plain media playback**
  on iPhone — behaviour that has shifted between iOS versions. If processed
  mode is silent on a phone, check the switch. iPads mostly have no such
  switch.

### Testing on a device

`serve.py` binds to localhost, so a phone cannot reach it. To test on real
hardware, serve to your wifi instead:

```bash
python3 serve.py 8800 --lan
```

or double-click `share-on-wifi.command`. It prints the URL to open on the
phone. This exposes the folder read-only to your local network while it runs,
so stop it when you are done.

None of the iOS behaviour above was verified on a real device from the machine
that built this — it is platform behaviour plus defensive handling. Test it on
the actual iPad and iPhone.

## Looping

The file is a **true loop**: it is rendered 10 seconds longer than needed and
that tail is folded back over the opening with an equal-power crossfade, so the
last sample runs naturally into the first. Measured at the seam: a 0.6 dB level
step and a sample discontinuity 46 dB below peak.

The length is deliberately a whole number of chord progressions
(8 × 192 s = 1536 s) so the harmony matches across the join.

Looping is left to the browser (`audio.loop = true`). An earlier version
crossfaded two `<audio>` decks to hide MP3 encoder padding; dropping MP3 removed
the reason for it, and dropping the crossfade is what allows the no-AudioContext
path above.

## Why it sounds like this

Every constraint is an attention-research constraint, then verified by
measurement against the finished file.

| intent | measured |
|---|---|
| no energy at 4–8 Hz — speech modulates there and the ear grabs it | **0.2%** of envelope energy |
| nothing swells enough to pull your eyes off the screen | **0.7 dB** across the middle 90% |
| dark — HF energy is arousing | tilts down steadily above 1 kHz |
| low dynamic range so nothing pops | crest factor **9.0 dB** |

Plus: no lyrics and nothing speech-shaped (irrelevant speech disrupts verbal
working memory); no beat, riff or section boundary (the changing-state effect);
45 ms bell attacks sitting ~7 dB under the bed (sharp onsets trigger the
orienting reflex); and all pitched material drawn from D minor pentatonic,
consonant against all six chords, moving by small random steps — so there is no
line to follow and nothing to anticipate.

The mix deliberately leaves a gap around 1–2 kHz. That is where speech
intelligibility lives, so keeping the music out of it lets the player's masking
noise do that job unopposed.

**Play it quieter than feels right** — roughly 45–55 dBA.

## Decisions worth knowing

- **Streaming `<audio>`, not `decodeAudioData`.** Decoding 25 minutes up front
  is ~250 MB of float PCM in the tab; phones will not tolerate that.
- **The audio graph is built lazily.** Not for performance — because its mere
  existence breaks background playback on iOS.
- **Custom `serve.py`.** `python -m http.server` does not implement Range, so
  `<audio>` cannot seek, which breaks the loop handover.
- **Equal-power crossfades** (still used for the pink-noise loop and the render's
  wrap). A linear pair dips in the middle on uncorrelated material, and an
  exponential ramp is undefined starting from a gain of 0 — which once silently
  swallowed a fade-in completely.
- **Clock on `setInterval`, meter on `setInterval`.** `requestAnimationFrame`
  does not fire at all in a backgrounded or offscreen tab — and this is music
  you leave running in another window.
- **40 Hz pulse off by default.** The auditory steady-state response does peak
  near 40 Hz, but the evidence it improves *focus* is thin. Offered, not
  asserted.

## Gotchas for future work

Four real bugs came out of this build. They are all easy to reintroduce.

1. **Never use two equal-amplitude oscillators at the same nominal pitch.**
   With independent drift their relative phase wanders and they sum to anywhere
   between 2× and *zero*. A duplicated D2 in the pedal swung the whole track
   **13 dB** on a ~12 s cycle. One oscillator per pedal pitch; get width from
   the pad and air instead.
2. **`np.convolve` is O(n·m)** and hangs for hours on a multi-second window over
   a long buffer. Use the `moving_avg` cumsum helper.
3. **A full-length float64 `cumsum` for oscillator phase** is a ~950 MB
   temporary *per oscillator* and drives the machine into swap. Phase is
   accumulated in 4M-sample chunks.
4. **`moving_avg` must replicate its edges, not zero-pad.** Zero padding makes
   the envelope read quiet at the file's head and tail, so the level rider
   boosts them.

And a measurement lesson: loudness was first checked in 45-second blocks, which
averaged the swell away entirely and reported 1.9 dB when the real short-term
spread was 12.7 dB. Check level at 1-second resolution, and check the envelope
spectrum to find *where* a modulation lives before trying to fix it.
