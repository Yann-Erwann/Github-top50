import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT_PATH / "src"

for path in (ROOT_PATH, SRC_PATH):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
