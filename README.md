# KaiaBooth

Kaia's DJ booth, without the Discord bot. Point it at your music library and she mixes
a set, live:

- **She picks what comes next the way a DJ does:** harmonically close (Camelot key),
  within a few percent of tempo (half/double time counts), the same kind of music where
  possible, nothing she played recently — and, once the library is measured, through a
  graph of which records actually *lock* with which, walked as hour-long sets.
- **The blends are real beatmatched mixes:** a counted bar, not a guessed one; the
  incoming record stretched with rubberband (and shifted a semitone when the keys
  clash); a two-bar bass handover; 32, 64 or 256-beat blends; an echo-out on the bar
  where nothing locks. Everything is levelled to a common loudness.
- **She rides the mixer** through the set — gain staging, trading mids, a bass kill in
  long blends — harder with her energy. Her mood (you set it) steers the opener.
- **The booth window** shows both decks and the mixer as she plays; NEXT, HANDS and the
  blend length are yours to press.

It is the records engine of [Kaiacord](../Kaiacord) (Kaia, a self-hosted Discord bot),
running the very same code. Where the bot plays into a voice channel, KaiaBooth plays on
your speakers — or writes the mix to a WAV.

## Install

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

System: `ffmpeg` built with librubberband, and an audio player (PipeWire's `pw-cat`,
`paplay`, `aplay` or `ffplay`). Optional: Essentia under the system Python, for
onset-accurate beat ticks (`tools/maintenance/beat_ticks.py`).

## Your library

KaiaBooth reads a `dj_catalog.json`: a list of records with their analysed BPM and key.

```json
[{"filepath": "/home/you/Music/Artist - Title.mp3", "artist": "Artist", "title": "Title",
  "bpm": 124, "key": "8A", "genre": "House"}]
```

`key` is a Camelot code. Point `music.library_catalog` at it in `config/local.yaml`:

```yaml
music:
  library_catalog: "~/Music/music/dj_catalog.json"
```

(Ekco's catalog is written by `arch-config/scripts/enhance_metadata.py`, which analyses
BPM and key with Essentia.)

## Use

```bash
venv/bin/python kaiabooth.py crate                      # what the catalog holds
venv/bin/python kaiabooth.py play                       # a set, on the speakers, with the booth window
venv/bin/python kaiabooth.py play "daft punk" --beats 256
venv/bin/python kaiabooth.py play --mood wired --minutes 45
venv/bin/python kaiabooth.py play --out mix.wav --minutes 20 --no-window   # record the mix instead
venv/bin/python kaiabooth.py sets --apply               # measure which records lock with which (slow, once)
```

The first sets measure new records in the background as they play; a run stops that
when it ends (it resumes next time), or `sets --apply` does it all up front.

## Working on it (and getting the work back into Kaiacord)

Most of the code is **shared with Kaiacord byte-for-byte** (listed in `sync.json`).
Improve it here, test it here, then:

```bash
python3 sync.py status   # what changed, on which side
python3 sync.py push     # copy your changes into ../Kaiacord (then test and commit there)
python3 sync.py pull     # take Kaiacord's changes
```

Rules for AI agents and people alike are in [CLAUDE.md](CLAUDE.md).

## Licence

The code is Kaiacord's (MIT, see Kaiacord).
