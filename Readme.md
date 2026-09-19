# Space Invaders Pro

A Space Invaders–style arcade shooter written in Python with [Pygame](https://www.pygame.org/): solo or
local two-player co-op, timed power-ups and a two-phase boss.

![Gameplay screenshot](space_invaders_cover.png)

## Run from source

Requires Python 3.11+ (tested locally on 3.13).

```bash
git clone https://github.com/udivak/Space-Invaders.git
cd Space-Invaders
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt   # Windows: .venv\Scripts\python
.venv/bin/python main.py
```

`python -m space_invaders` from the repository root starts the same game. `main.py` also works when
started by absolute path from any directory.

The checked-in `Space Invaders Pro.exe` predates this version and has not been rebuilt or validated; see
[docs/BUILD.md](docs/BUILD.md) for the reproducible Windows build procedure.

## Controls

| Mode | Move | Fire |
| --- | --- | --- |
| Solo | Arrow keys | Space |
| Co-op player 1 (blue) | Arrow keys | L |
| Co-op player 2 (orange) | W A S D | G |

Menus work with the mouse or keyboard (arrows / Tab, Enter). Esc pauses a run (Resume, Restart, Menu,
Quit); losing window focus also pauses.

## Rules

- Holding fire builds heat; at full heat you must release fire to cool down.
- An enemy reaching the bottom costs one of 5 breaches. Touching an enemy costs 15 health; touching a
  boss ends the run. Enemy shots deal 10.
- Enemies arrive one every 0.75 s from the top in six lanes. Blue enemies weave side to side.
- A boss appears on odd levels from 3, after a one-second warning. Below half health it telegraphs and
  switches to a three-shot spread.
- Packs: health refill, triple shot for 12 seconds (refreshes, does not stack), shield that blocks three
  projectiles. Effects carry across waves.
- Each wave restores one breach and up to 20 health.
- Score: 1 point per enemy destroyed by a shot, 10 per boss defeated. Co-op records one team score and
  ends when either ship is destroyed.

## Scores and settings

Scores (`scores.csv`) and settings (`settings.json`) are stored per user:

| Platform | Location |
| --- | --- |
| Windows | `%LOCALAPPDATA%\SpaceInvaders` |
| macOS | `~/Library/Application Support/SpaceInvaders` |
| Linux | `$XDG_DATA_HOME/space-invaders` (default `~/.local/share/space-invaders`) |

Set `SPACE_INVADERS_DATA_DIR` to an absolute directory to use another location. The scores screen shows
the Top 10 for each mode and ruleset; use Left/Right to switch groups, including the imported legacy
history.

When run from source for the first time, the repository's old `scores.txt` is imported as legacy records
and left unchanged. A `scores.txt` that is not UTF-8 is shown read-only and not imported until you name its
encoding, e.g. `SPACE_INVADERS_LEGACY_ENCODING=cp1252`. Settings offer music volume, effects volume and a
reduced-effects mode. Without an audio device the game runs silently.

## Tests

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q                  # everything
.venv/bin/python -m pytest -q -m integration   # real media, lifecycle and fresh-process startup
```

Tests use dummy SDL drivers and temporary data directories; they never touch your scores.

## Project documents

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — modules and invariants
- [docs/CREDITS.md](docs/CREDITS.md) — asset provenance (incomplete; see file)
- [docs/BUILD.md](docs/BUILD.md) — Windows build procedure
- [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) and [docs/PROGRESS.md](docs/PROGRESS.md)

No license has been chosen for the code yet, and asset licenses are unverified.
