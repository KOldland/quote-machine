import os
import sys
from pathlib import Path
import pytest

# Ensure local app imports work in test mode.
os.environ.setdefault("QM_TEST_MODE", "1")
os.environ.setdefault("QM_SECRET_KEY", "test-secret-key")

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from QMapp import app as flask_app


@pytest.fixture
def client():
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_admin(client):
    """Session fixture that logs in an admin user."""
    with client.session_transaction() as sess:
        sess["role"] = "admin"
        sess["username"] = "test-admin"
    yield client
