import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data_audit"))
from prepare_isot import DATA_DIR  # noqa: E402,F401
