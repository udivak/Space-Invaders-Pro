# PyInstaller spec for the Windows x64 one-folder candidate (Task 7.3).
# Build natively on Windows: python -m PyInstaller --clean --noconfirm SpaceInvaders.spec
# Includes only runtime media; never scores, settings or development environments.

a = Analysis(
    ["main.py"],
    pathex=["."],
    datas=[("assets", "assets"), ("sounds", "sounds")],
    excludes=["pytest", "tests"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SpaceInvaders", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="SpaceInvaders")
