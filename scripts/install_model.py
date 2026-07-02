"""
Small helper to place a local `best.pt` into the project's expected model path.

Usage:
  python scripts/install_model.py /path/to/best.pt

This copies the file into `models/best.pt` inside the project parent folder
used by `server.py` (one of the `MODEL_CANDIDATES`).
"""
import shutil
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/install_model.py /path/to/best.pt")
        return
    src = sys.argv[1]
    if not os.path.exists(src):
        print(f"Source file not found: {src}")
        return

    # target relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(project_root, "models")
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, "best.pt")

    shutil.copy2(src, target)
    print(f"Copied {src} -> {target}")

if __name__ == '__main__':
    main()
