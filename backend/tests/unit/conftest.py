import os, sys
import pytest
import warnings as _warnings

# Ensure backend dir on sys.path for unit tests
HERE = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, BACKEND_DIR)

# Test-only warning filters to reduce noise
_warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r"Using SQLAlchemy.*LegacyAPIWarning.*",
)
_warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r"Using the in-memory storage for tracking rate limits.*",
)

@pytest.fixture(autouse=True, scope="session")
def _suppress_deprecation_warnings():
    _warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r"Using SQLAlchemy.*LegacyAPIWarning.*",
    )
    _warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message=r"Using the in-memory storage for tracking rate limits.*",
    )
