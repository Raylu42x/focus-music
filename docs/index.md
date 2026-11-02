# Deep Work docs

[../README.md](../README.md) is the full reference for this project. This page helps you find things in it.

| You want to | README section |
|---|---|
| Publish a change | Deployment |
| Run it locally | Run it locally |
| Know what each file is | Files |
| Regenerate the audio | Files, and Looping before changing the length |
| Understand phone playback | Phones |
| Know why it sounds this way | Why it sounds like this |
| Avoid known traps | Decisions worth knowing, Gotchas for future work |

## Rules worth remembering

- The site is three static files plus audio, with no build step. Pushing to `main` publishes to
  `focus.kervian.com` through GitHub Pages.
- Keep `CYCLES` in `focus_synth.py` a whole number, or the loop breaks.
- `index.html` is the desktop player and `ios.html` is the phone player, which never uses an AudioContext.
- The FLAC master and WAV render are not in git. Re-rendering with `python3 focus_synth.py` takes about 3 minutes.
