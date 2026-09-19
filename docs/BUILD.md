# Windows build (release candidate)

Status: **not built.** The procedure below has not been run; no candidate or checksum exists yet. It must
be built and checked on native Windows x64 — macOS/Linux cannot produce or validate it.

## Build

From the repository root, with Python 3.13 x64 on Windows:

```powershell
python -m venv .venv-build
.venv-build\Scripts\python -m pip install -r requirements-build.txt
.venv-build\Scripts\python -m PyInstaller --clean --noconfirm SpaceInvaders.spec
Compress-Archive -Path dist/SpaceInvaders -DestinationPath dist/SpaceInvaders-win-x64.zip -Force
Get-FileHash dist/SpaceInvaders-win-x64.zip -Algorithm SHA256
```

`SpaceInvaders.spec` builds a one-folder bundle from `main.py` and copies `assets/` and `sounds/` beside
the package so resources resolve the same way as from source. It includes no scores, settings or
development environment. In a frozen build, the repository's `scores.txt` is never imported.

Record the Python, Pygame and PyInstaller versions, the source commit and the SHA-256 here once built.
If the pinned PyInstaller version is replaced, pin the version that was actually validated.

## Required native checks

Run the built `dist/SpaceInvaders/SpaceInvaders.exe` (ideally on a machine without Python):

- clean user profile; start from a different working directory; install folder read-only
- no audio device; both modes; boss at level 3; pause/resume/restart
- save a score with a Unicode name, view scores, change settings and restart to confirm persistence
- confirm files appear only under `%LOCALAPPDATA%\SpaceInvaders`

Keep the old `Space Invaders Pro.exe` until this candidate passes these checks.
