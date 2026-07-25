#!/usr/bin/env python3
"""
Builds the standalone backend exe and stages Stockfish for Electron packaging.

Run from the repo root: python build_backend.py
Output:
  tier2-ui/resources/backend/jarvis-backend.exe
  tier2-ui/resources/backend/stockfish/stockfish.exe (if found)
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "tier2-ui", "resources", "backend")
# Matches engine.py's own default Windows lookup path, so a local dev machine
# that already has Stockfish set up (see setup_stockfish.py) needs no extra
# config; CI sets STOCKFISH_SRC after downloading it fresh.
STOCKFISH_SRC = os.environ.get("STOCKFISH_SRC", r"C:\stockfish\stockfish.exe")


def main():
    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller", "backend.spec",
            "--noconfirm",
            "--distpath", OUT_DIR,
            "--workpath", os.path.join(ROOT, "build", "backend_work"),
        ],
        cwd=ROOT,
        check=True,
    )

    if os.path.exists(STOCKFISH_SRC):
        dest_dir = os.path.join(OUT_DIR, "stockfish")
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(STOCKFISH_SRC, os.path.join(dest_dir, "stockfish.exe"))
        print(f"Copied Stockfish from {STOCKFISH_SRC}")
    else:
        print(
            f"WARNING: Stockfish not found at {STOCKFISH_SRC} (set STOCKFISH_SRC to override) "
            "- the packaged app will start but JARVIS won't be able to move.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
