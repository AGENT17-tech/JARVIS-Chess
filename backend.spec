# PyInstaller spec for the Tier 2 FastAPI backend, bundled as a standalone
# onefile exe so the Electron desktop app doesn't require a Python install.
#
# Build:  pyinstaller backend.spec
# Output: dist/jarvis-backend.exe
#
# main.py's `serve` subcommand hands uvicorn the app as the string
# "api_server:app" (see cmd_serve in main.py), so api_server — and
# everything it imports — must be pulled in explicitly via hiddenimports;
# PyInstaller's static analysis can't follow a runtime string import.

a = Analysis(
    ['main.py'],
    # Needed so hiddenimports below can be resolved even for modules main.py
    # never references (directly or via a function-local import) — e.g.
    # api_server.py, which uvicorn only imports at runtime by string name.
    pathex=[SPECPATH],
    binaries=[],
    datas=[('resources/openings', 'resources/openings')],
    hiddenimports=[
        'api_server',
        'game_engine',
        'engine',
        'openingbook',
        'openingtracker',
        'moveanalyzer',
        'pgnhandler',
        'database',
        'chesscom_integration',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='jarvis-backend',
    console=True,
    onefile=True,
)
