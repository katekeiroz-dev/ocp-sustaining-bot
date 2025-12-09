"""
Pytest configuration and fixtures for slack_worker tests
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    mock_cfg = Mock()
    mock_cfg.SLACK_BOT_TOKEN = "xoxb-test-token"
    mock_cfg.SLACK_APP_TOKEN = "xapp-test-token"
    mock_cfg.ROTA_SERVICE_ACCOUNT = {"type": "service_account"}
    mock_cfg.ROTA_USERS = {
        "john.doe": "U12345",
        "jane.smith": "U67890",
        "bob.wilson": "U24680"
    }
    mock_cfg.ROTA_ADMINS = {"admin": "U99999"}
    mock_cfg.ROTA_GROUP_CHANNEL = "C12345"
    mock_cfg.ROTA_SHEET = "ROTA"
    mock_cfg.ROTA_SYNC_WORKSHEET = "Smartsheet_Sync"
    mock_cfg.ASSIGNMENT_WORKSHEET = "Assignments"
    mock_cfg.SMARTSHEET_ACCESS_TOKEN = "smartsheet-token"
    mock_cfg.SMARTSHEET_SHEET_ID = "sheet-id-123"
    mock_cfg.SCHEDULE_GROUP_REMINDER = "0 9 * * MON,THU"
    mock_cfg.SCHEDULE_DM_REMINDER_FRIDAY = "0 17 * * FRI"
    mock_cfg.SCHEDULE_DM_REMINDER_MONDAY = "0 9 * * MON"
    mock_cfg.SCHEDULE_SHEET_SYNC = "0 8 * * *"
    mock_cfg.LOCK_DIR = "/tmp/test_locks"
    mock_cfg.LOCK_TIMEOUT = 300
    mock_cfg.ENABLE_GROUP_REMINDER = True
    mock_cfg.ENABLE_DM_REMINDER = True
    mock_cfg.ENABLE_SHEET_SYNC = True
    mock_cfg.TIMEZONE = "UTC"
    mock_cfg.LOG_LEVEL = "INFO"
    mock_cfg.ROTA_LEADS = ["lead1", "lead2"]
    mock_cfg.ROTA_MEMBERS = ["member1", "member2", "member3"]
    return mock_cfg


@pytest.fixture
def mock_slack_client():
    """Mock Slack client for testing"""
    client = Mock()
    client.send_message = Mock(return_value=True)
    client.send_dm = Mock(return_value=True)
    client.get_user_info = Mock(return_value={"id": "U12345", "name": "testuser"})
    return client


@pytest.fixture
def mock_gsheet():
    """Mock GSheet for testing"""
    gsheet = Mock()
    gsheet.fetch_data_by_time = Mock(return_value=[])
    gsheet.fetch_data_by_release = Mock(return_value=[])
    return gsheet


@pytest.fixture
def sample_releases():
    """Sample release data for testing"""
    return [
        {
            'release_version': '4.15.1',
            'start_date': '2024-01-08',
            'end_date': '2024-01-12'
        },
        {
            'release_version': '4.16.2',
            'start_date': '2024-01-15',
            'end_date': '2024-01-19'
        }
    ]


@pytest.fixture
def sample_rota_data():
    """Sample ROTA data from Google Sheets"""
    return [
        ['4.15.1', '2024-01-08', '2024-01-12', 'john.doe', 'jane.smith', 'bob.wilson', 'This Week'],
        ['4.16.2', '2024-01-15', '2024-01-19', 'jane.smith', 'bob.wilson', 'john.doe', 'Next Week']
    ]


@pytest.fixture(autouse=True)
def cleanup_lock_dir():
    """Clean up lock directory after each test"""
    yield
    # Cleanup after test
    lock_dir = Path("/tmp/test_locks")
    if lock_dir.exists():
        for lock_file in lock_dir.glob("*.lock"):
            try:
                lock_file.unlink()
            except:
                pass

