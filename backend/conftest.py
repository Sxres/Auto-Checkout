import sys
from pathlib import Path

import pytest

# The capture API imports the shared Store as a top-level module (ml/scripts/store.py);
# make it importable here the same way ml/tests/conftest.py does for the pipeline scripts.
sys.path.insert(0, str(Path(__file__).parents[1] / "ml" / "scripts"))


@pytest.fixture(autouse=True)
def _reset_catalog_cache():
    # /recognize caches the catalog by store root; moto buckets are recreated per test, so
    # clear it before and after each test to avoid serving a stale catalog.
    from app.catalog import reset_catalog

    reset_catalog()
    yield
    reset_catalog()