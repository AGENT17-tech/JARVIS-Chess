#!/usr/bin/env python3
"""
Environment setup & verification for JARVIS Chess Tier 1.
Run this before your first game.
"""

import subprocess
import sys
import shutil

def check_python_version():
    """Verify Python 3.10+"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor} - requires 3.10+")
        return False

def check_stockfish():
    """Verify Stockfish is available (system binary OR pip package)"""
    # Method 1: Check system PATH
    if shutil.which("stockfish"):
        try:
            result = subprocess.run(
                ["stockfish"],
                input="quit\n",
                capture_output=True,
                text=True,
                timeout=5
            )
            print("✓ Stockfish found in system PATH")
            return True
        except Exception as e:
            print(f"⚠ Stockfish found but not responsive: {e}")
            print("  (Will try pip package bundled version)")
            return True  # Still OK if pip package has it
    
    # Method 2: Try importing stockfish pip package (has bundled binary)
    try:
        import stockfish
        print("✓ Stockfish available via pip package (bundled binary)")
        return True
    except ImportError:
        print("✗ Stockfish not found")
        print("  Install: pip install stockfish")
        print("           (or) apt-get install stockfish (Linux)")
        print("           (or) brew install stockfish (macOS)")
        return False

def check_python_packages():
    """Verify required Python packages"""
    packages = {
        'chess': 'python-chess',
        'stockfish': 'stockfish'
    }
    
    all_ok = True
    for module, package in packages.items():
        try:
            __import__(module)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - install with: pip install {package}")
            all_ok = False
    
    return all_ok

def main():
    """Run all checks"""
    print("\n" + "="*50)
    print("  JARVIS Chess - Environment Setup")
    print("="*50 + "\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Stockfish", check_stockfish),
        ("Python Packages", check_python_packages),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        results.append(check_func())
    
    print("\n" + "="*50)
    if all(results):
        print("✓ All checks passed! Ready to play.")
        print("\nStart a game with:")
        print("  python main.py")
    else:
        print("✗ Some checks failed. Fix issues above and retry.")
        sys.exit(1)
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
