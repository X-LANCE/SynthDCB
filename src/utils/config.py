"""Project-level paths and non-service configuration."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEVICES_DIR = PROJECT_ROOT / "simulator" / "devices"
DOMAIN_CONFIG_DIR = PROJECT_ROOT / "simulator" / "domains"
DATA_DIR = PROJECT_ROOT / "data"
RUN_DIR = PROJECT_ROOT / "run"
RESULTS_DIR = PROJECT_ROOT / "results"
LOG_DIR = RUN_DIR

# Kept as strings for callers that serialize configuration.
PROJECT_ROOT_ = str(PROJECT_ROOT)
LOG_DIR_ = str(LOG_DIR)

DEFAULT_MAX_REVIEW_ROUNDS = 2
