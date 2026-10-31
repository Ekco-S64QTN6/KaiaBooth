# CLAUDE.md — KaiaBooth

KaiaBooth is Kaia's DJ from the Kaiacord Discord bot, runnable on its own: she mixes
your record library live — beat-gridded, key-aware blends chosen from a measured graph
of which records lock with which, stretched with rubberband, ridden on the mixer with
her own hands — with the DJ booth window (decks, mixer, NEXT, HANDS). **Kaiacord is the
mother project.** This repo exists so the DJ can be worked on, tested and used without
the bot, and every improvement goes back to Kaiacord.

## The one rule: shared files stay byte-identical with Kaiacord

`sync.json` lists the **shared files** (`utils/audio/` records and booth, `assets/dj/`,
some tools and tests). They are copies of Kaiacord's files at the same relative path, and the same file
runs in both places. Everything else is **standalone-only** and says so in its header.

| Shared (edit carefully, it runs in Kaiacord too) | Standalone-only (this repo's own) |
|:--|:--|
| `utils/audio/records.py`, `library.py`, `beatgrid.py`, `setlist.py`, `dj_dashboard.py`, … (see `sync.json`) | `kaiabooth.py` (entry point), `standalone/` (bootstrap, discord stand-in, `speaker.py`), `utils/core/kaia_art_intent.py` (mood), `utils/infrastructure/system/yaml_config.py`, `config/`, `conftest.py`, `sync.py`, docs |

So, for a shared file:

- **Don't add standalone hacks to it.** If the standalone needs different behaviour, put it
  in a standalone-only file (the entry point, `standalone/`, the config loader) — or make
  the shared code configurable through `config.get(...)` with Kaiacord's default unchanged.
- **Don't rename or move it** without doing the same in Kaiacord (and `sync.json`).
- **It must still work inside Kaiacord**, where `discord` is the real library and the bot,
  Ollama and the voice thread are running. Kaiacord's rules for this code apply here
  unchanged: read `docs/kaiacord/CLAUDE.md` (a read-only copy, refreshed by `sync.py pull`):
  §7 "Music Engine" from "`!music records` mixes the local library" on (stretching, the
  bar, blends, levels — each rule learned from a mix that sounded wrong), §9 (logging,
  telemetry that lies, check the payload), §11 (working practice).
- **Kaia's mood** is `utils/core/kaia_art_intent.py` here, a standalone stand-in for the
  two functions the music reads (`mood`, `feeling_word`). In Kaiacord the same path is her
  live mood engine and her art; don't add it to `sync.json`.
- New shared files: add them in Kaiacord first (or here, then list them in `sync.json`
  and push), so both sides have them.

## Workflow

```bash
python3 sync.py pull                 # before starting: take Kaiacord's latest
# … work, then test here:
venv/bin/python -m pytest -q
python3 sync.py status               # what you changed (local), what Kaiacord changed (upstream)
python3 sync.py push                 # send your shared-file changes to ../Kaiacord
# then in Kaiacord: run its suite and commit there (its CLAUDE.md §2, §13)
```

`sync.lock.json` records each shared file's hash at the last sync (commit it; never edit
it by hand). A file changed on both sides is a **conflict**: merge by hand, then
`sync.py pull --force PATH` or `push --force PATH`. A push never deletes a file in
Kaiacord unless named with `--force`.

## Tests

`venv/bin/python -m pytest -q` runs Kaiacord's records tests unchanged (`tools/tests/`,
shared) plus this repo's own (`tests/`). A shared test that needs a Kaiacord-only module
(the bot's background tasks, the RAG index) is reported as *skipped: Kaiacord-only*, by
`conftest.py`; any other failure is real. Add tests for shared code to the shared test
files (or a new shared test file) so Kaiacord runs them too.

## Running

`python3 kaiabooth.py --help`. Settings in `config/local.yaml` override
`config/default_config.yaml` (same keys as Kaiacord's `music:` section; set
`music.library_catalog`). The set graph and beat ticks go to `memory/records/`, logs to
`logs/kaiabooth.log`, both git-ignored. The mix plays through `standalone/speaker.py`
(pw-cat / paplay / aplay / ffplay), or into a WAV with `--out`.

## Verify behaviour, not just syntax

As in Kaiacord: a change is done when you have heard it work — a real set from the
library (`kaiabooth.py play`), or a mix written with `--out` and measured (onsets, levels,
the blend) — not when the tests pass. "No late frames or buffer underruns" at the end of a
set is the mixer's own report; the WAV is the evidence.
