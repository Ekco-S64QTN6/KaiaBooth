#!/usr/bin/env python3
"""KaiaBooth — Kaia's DJ booth: your record library, mixed live, without the Discord bot.

STANDALONE-ONLY FILE: the entry point. Everything it drives is Kaiacord's own code
(utils/audio/records.py and friends, shared byte-for-byte; see sync.py). Where
Kaiacord plays the mix into a Discord voice channel, this plays it on your speakers
(standalone/speaker.py) — the same frames, read the same way.

    python3 kaiabooth.py play                    a set: the next pre-measured set, or an opener for her mood
    python3 kaiabooth.py play "daft punk"        start from a record matching the words
    python3 kaiabooth.py play --mood wired --beats 256 --minutes 30
    python3 kaiabooth.py play --out mix.wav --minutes 10    record the mix to a file instead of playing it
    python3 kaiabooth.py crate                   what the catalog holds
    python3 kaiabooth.py sets [--apply]          measure which records lock with which (tools/maintenance/records_graph.py)

The booth window (decks, mixer, NEXT, HANDS) opens with a set; `--no-window` keeps
it closed (it is still served). Settings: config/default_config.yaml, overridden by
config/local.yaml — at least `music.library_catalog`.
"""
from __future__ import annotations

import standalone.bootstrap  # noqa: F401  (working directory, log file, discord stand-in)

import argparse
import asyncio
import inspect
import os
import signal
import sys
import time
from pathlib import Path


def _say(text: str) -> None:
    print(text, flush=True)


def _crate():
    from utils.audio import library
    from utils.infrastructure.system.yaml_config import config
    catalog = os.path.expanduser(str(config.get("music.library_catalog", "") or ""))
    if not catalog:
        sys.exit("no record library: set music.library_catalog in config/local.yaml (a dj_catalog.json)")
    crate = library.load(catalog)
    if not crate:
        sys.exit(f"{catalog}: no playable records (missing file, or every entry's audio is gone)")
    return crate


async def cmd_play(a) -> int:
    from datetime import datetime
    from utils.audio import library, records, setlist
    from utils.core.kaia_art_intent import feeling_word, mood
    from utils.infrastructure.system.yaml_config import config
    from standalone.speaker import SpeakerChannel
    if a.mood:
        os.environ["KAIA_MOOD"] = a.mood
    if a.no_window:
        config.set("music.dj_dashboard", False)
    crate = await asyncio.to_thread(_crate)
    chosen = None
    if a.query:
        first = library.find(crate, a.query)
        if not first:
            _say(f"nothing in the crate matches {a.query!r}")
            return 1
        why = "you asked for it"
    else:
        # As Kaiacord's `!music records`: the next of the pre-measured sets, else her mood's opener.
        chosen = setlist.next_set(await asyncio.to_thread(setlist.load), crate)
        by_path = {r.path: r for r in crate}
        first = by_path.get(chosen[0]) if chosen else None
        why = f"the start of a set of {len(chosen)} that all lock together" if first else \
            f"for the mood she's in ({feeling_word(mood())})"
        first = first or library.opener(crate, mood(), datetime.now().hour)
    channel = SpeakerChannel(out=Path(a.out) if a.out else None)
    session = await records.start_records(
        channel, crate, first, requested_by="you",
        mix_beats=int(a.beats or config.get("music.records_mix_beats", 64)),
        alone_grace_s=float(config.get("music.alone_grace_seconds", 120)),
        set_list=chosen if not a.query and chosen and first.path == chosen[0] else None)
    from utils.audio import dj_dashboard
    _say(f"starting with {first.name} ({first.bpm:g} bpm, {first.key or '?'}), {why}. "
         f"{len(crate)} records in the crate. booth: {dj_dashboard.url() or 'off'}"
         + (f"  → writing {a.out}" if a.out else "") + "  (Ctrl+C to stop)")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    end = time.time() + a.minutes * 60 if a.minutes else None
    last = None
    while not stop.is_set() and not session._closing and (end is None or time.time() < end):
        now = session.names[-1] if session.names else None
        if now and now != last:
            _say(f"  ▶ {now}")
            last = now
        try:
            await asyncio.wait_for(stop.wait(), 1.0)
        except asyncio.TimeoutError:
            pass
    await session.stop()
    _say(f"set over: {len(session.names)} records.")
    if not a.keep_measuring and (n := _stop_measuring()):
        _say(f"stopped the background measuring of the crate ({n} process); it picks up where it left off "
             "next time, or run `kaiabooth.py sets --apply` to finish it")
    return 0


def _stop_measuring() -> int:
    """A set start measures new records in a separate process (setlist.build_in_background)
    that Kaiacord, always running, lets finish. A command-line run should not leave it
    behind: stop the one this process started. The graph is extended, never rebuilt,
    so what was measured is kept."""
    import signal as _signal
    me, n = os.getpid(), 0
    for stat in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = stat.read_text().rsplit(")", 1)[1].split()
            if int(fields[1]) != me:
                continue
            cmd = (stat.parent / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except (OSError, ValueError, IndexError):
            continue
        if "records_graph.py" in cmd:
            os.kill(int(stat.parent.name), _signal.SIGTERM)
            n += 1
    return n


def cmd_crate(a) -> int:
    from collections import Counter
    crate = _crate()
    _say(f"{len(crate)} records")
    genres = Counter(r.genre or "?" for r in crate)
    _say("genres: " + ", ".join(f"{g} {n}" for g, n in genres.most_common(12)))
    bpms = sorted(r.bpm for r in crate if r.bpm)
    if bpms:
        _say(f"tempo: {bpms[0]:g}–{bpms[-1]:g} bpm, median {bpms[len(bpms) // 2]:g}")
    return 0


def cmd_sets(a) -> int:
    import runpy
    sys.argv = ["records_graph.py"] + (["--apply"] if a.apply else [])
    runpy.run_path("tools/maintenance/records_graph.py", run_name="__main__")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="kaiabooth", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("play", help="mix a set")
    p.add_argument("query", nargs="?", help="start from a record matching these words")
    p.add_argument("--mood", help="wired, restless, tired, hollow, bright, heavy, calm or curious")
    p.add_argument("--beats", type=int, choices=(32, 64, 256), help="blend length (default music.records_mix_beats)")
    p.add_argument("--minutes", type=float, help="stop after this long")
    p.add_argument("--out", help="write the mix to this WAV instead of the speakers")
    p.add_argument("--no-window", action="store_true", help="don't open the booth window")
    p.add_argument("--keep-measuring", action="store_true",
                   help="leave the background measuring of new records running after the set")
    sub.add_parser("crate", help="what the catalog holds")
    s = sub.add_parser("sets", help="measure which records lock with which")
    s.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    fn = {"play": cmd_play, "crate": cmd_crate, "sets": cmd_sets}[a.cmd]
    return asyncio.run(fn(a)) if inspect.iscoroutinefunction(fn) else fn(a)


if __name__ == "__main__":
    sys.exit(main())
