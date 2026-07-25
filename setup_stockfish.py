#!/usr/bin/env python3
"""
Automatic Stockfish binary setup for Windows.
Downloads and extracts Stockfish to C:\stockfish\
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

# Windows consoles often default to a legacy codepage (e.g. cp1252) that
# can't encode the checkmark/cross characters used below; force UTF-8 so
# this script doesn't crash mid-setup after a successful download/extract.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

STOCKFISH_DIR = r"C:\stockfish"
STOCKFISH_EXE = os.path.join(STOCKFISH_DIR, "stockfish.exe")

# Latest Stockfish Windows binary
STOCKFISH_URL = "https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-windows-x86-64.zip"

def download_stockfish():
    """Download Stockfish binary."""
    print("\n" + "="*60)
    print("  Downloading Stockfish binary...")
    print("="*60)
    
    # Create directory
    Path(STOCKFISH_DIR).mkdir(parents=True, exist_ok=True)
    
    zip_path = os.path.join(STOCKFISH_DIR, "stockfish.zip")
    
    try:
        print(f"Downloading from: {STOCKFISH_URL}")
        print(f"Saving to: {zip_path}")
        
        # Download with progress
        def download_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(downloaded * 100 // total_size, 100)
            print(f"\r  Progress: {percent}%", end="", flush=True)
        
        urllib.request.urlretrieve(STOCKFISH_URL, zip_path, download_progress)
        print("\n✓ Download complete")
        
        return zip_path
    
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        return None

def extract_stockfish(zip_path):
    """Extract Stockfish binary."""
    print("\nExtracting archive...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all files
            zip_ref.extractall(STOCKFISH_DIR)
        
        print("✓ Extraction complete")
        
        # Find the executable. Official release archives name the binary
        # after the target (e.g. "stockfish-windows-x86-64.exe"), not
        # plain "stockfish.exe", so match any stockfish*.exe.
        for root, dirs, files in os.walk(STOCKFISH_DIR):
            for file in files:
                if file.lower().startswith("stockfish") and file.lower().endswith(".exe"):
                    source = os.path.join(root, file)
                    dest = STOCKFISH_EXE

                    # Move to root if in subfolder
                    if source != dest:
                        shutil.move(source, dest)
                        print(f"✓ Stockfish moved to: {dest}")

                    return True
        
        print("✗ stockfish.exe not found in archive")
        return False
    
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        return False

def verify_stockfish():
    """Verify Stockfish works."""
    print("\nVerifying Stockfish...")
    
    if not os.path.exists(STOCKFISH_EXE):
        print(f"✗ Stockfish not found at: {STOCKFISH_EXE}")
        return False
    
    try:
        import subprocess
        result = subprocess.run(
            [STOCKFISH_EXE],
            input=b"quit\n",
            capture_output=True,
            timeout=5
        )
        print(f"✓ Stockfish verified at: {STOCKFISH_EXE}")
        return True
    
    except Exception as e:
        print(f"✗ Stockfish verification failed: {e}")
        return False

def cleanup_zip(zip_path):
    """Remove download zip file."""
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
            print("✓ Cleaned up temporary files")
    except:
        pass

def main():
    """Main setup flow."""
    print("\n" + "="*60)
    print("  JARVIS Chess - Stockfish Auto-Setup")
    print("="*60)
    
    # Check if already installed
    if os.path.exists(STOCKFISH_EXE):
        print(f"\n✓ Stockfish already installed at: {STOCKFISH_EXE}")
        verify_stockfish()
        print("\n✓ Setup complete! Run: python main.py")
        return True
    
    print(f"\nStockfish will be installed to: {STOCKFISH_DIR}")
    print("This requires ~20MB download\n")
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Setup cancelled")
        return False
    
    # Download
    zip_path = download_stockfish()
    if not zip_path:
        return False
    
    # Extract
    if not extract_stockfish(zip_path):
        return False
    
    # Verify
    if not verify_stockfish():
        return False
    
    # Cleanup
    cleanup_zip(zip_path)
    
    print("\n" + "="*60)
    print("✓ Setup complete!")
    print("="*60)
    print("\nStockfish installed successfully!")
    print(f"Location: {STOCKFISH_EXE}")
    print("\nNext step: python main.py")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
