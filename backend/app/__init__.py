"""Auto Vision Checkout API."""

import sys
from pathlib import Path

# The capture API reuses the pipeline's shared Store (ml/scripts/store.py) as a top-level
# module. Make it importable when running from source (uvicorn, pytest); the Lambda image
# ships store.py at the app root instead, so this is a no-op there.
_scripts = Path(__file__).resolve().parents[2] / "ml" / "scripts"
if _scripts.is_dir() and str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
