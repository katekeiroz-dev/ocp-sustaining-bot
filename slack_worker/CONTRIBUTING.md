# Contributing to Slack Worker Service

## Development Setup

### Prerequisites

- Python 3.12+
- Docker (for containerized testing)
- Access to development Slack workspace
- Access to test Google Sheets

### Local Development

1. **Clone and setup**:
```bash
cd slack_worker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your test credentials
```

3. **Run tests**:
```bash
pytest tests/ -v
```

4. **Run locally**:
```bash
python -m slack_worker.main
```

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use descriptive variable names

### Example:

```python
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def process_releases(releases: List[Dict]) -> bool:
    """
    Process release data and send notifications.
    
    Args:
        releases: List of release dictionaries
    
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Processing {len(releases)} releases")
    
    for release in releases:
        # Process each release
        pass
    
    return True
```

## Adding New Features

### Adding a New Scheduled Job

1. **Create job module** in `slack_worker/jobs/`:

```python
# jobs/my_feature.py
import logging

logger = logging.getLogger(__name__)


def my_scheduled_job():
    """
    Description of what this job does.
    This will be called by the scheduler.
    """
    logger.info("Starting my scheduled job")
    
    try:
        # Job implementation
        pass
        
        logger.info("Completed my scheduled job")
        
    except Exception as e:
        logger.error(f"Error in my scheduled job: {e}", exc_info=True)
        raise
```

2. **Add to jobs `__init__.py`**:

```python
from .my_feature import my_scheduled_job

__all__ = [
    # ... existing jobs
    'my_scheduled_job',
]
```

3. **Register in scheduler** (`main.py`):

```python
from slack_worker.jobs import my_scheduled_job

def setup_jobs(scheduler):
    # ... existing jobs
    
    if config.ENABLE_MY_FEATURE:
        scheduler.add_cron_job(
            func=my_scheduled_job,
            job_id='my_feature_job',
            cron_expression=config.SCHEDULE_MY_FEATURE,
            use_lock=True
        )
```

4. **Add configuration** (`config.py`):

```python
SCHEDULE_MY_FEATURE = os.getenv('SCHEDULE_MY_FEATURE', '0 10 * * *')
ENABLE_MY_FEATURE = os.getenv('ENABLE_MY_FEATURE', 'true').lower() == 'true'
```

5. **Write tests** (`tests/test_my_feature.py`):

```python
import pytest
from unittest.mock import Mock, patch
from slack_worker.jobs.my_feature import my_scheduled_job


class TestMyScheduledJob:
    """Test my scheduled job"""
    
    @patch('slack_worker.jobs.my_feature.some_dependency')
    def test_my_scheduled_job_success(self, mock_dep, mock_config):
        """Test successful execution"""
        with patch('slack_worker.jobs.my_feature.config', mock_config):
            mock_dep.return_value = "success"
            
            my_scheduled_job()
            
            mock_dep.assert_called_once()
    
    @patch('slack_worker.jobs.my_feature.some_dependency')
    def test_my_scheduled_job_error(self, mock_dep, mock_config):
        """Test error handling"""
        with patch('slack_worker.jobs.my_feature.config', mock_config):
            mock_dep.side_effect = Exception("Test error")
            
            with pytest.raises(Exception):
                my_scheduled_job()
```

### Adding Configuration Options

1. Add to `config.py`:
```python
MY_NEW_SETTING = os.getenv('MY_NEW_SETTING', 'default_value')
```

2. Add to `.env.example`:
```bash
# My new setting description
MY_NEW_SETTING=default_value
```

3. Update `README.md` configuration section

4. Update Kubernetes ConfigMap/Secret if needed

## Testing Guidelines

### Writing Tests

- Test both success and failure cases
- Use mocks for external dependencies (Slack API, Google Sheets, etc.)
- Aim for >80% code coverage
- Test edge cases

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_my_feature.py -v

# With coverage
pytest tests/ --cov=slack_worker --cov-report=html

# Specific test
pytest tests/test_my_feature.py::TestMyFeature::test_specific_case -v
```

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch


class TestFeatureName:
    """Test suite for feature"""
    
    def test_basic_functionality(self):
        """Test basic case"""
        # Arrange
        expected = "result"
        
        # Act
        result = function_to_test()
        
        # Assert
        assert result == expected
    
    @patch('module.dependency')
    def test_with_mock(self, mock_dep):
        """Test with mocked dependency"""
        mock_dep.return_value = "mocked"
        
        result = function_to_test()
        
        assert result == "expected"
        mock_dep.assert_called_once()
```

## Docker Testing

### Build and Test Locally

```bash
# Build image
docker build -f Dockerfile -t slack-worker:test ..

# Run with docker-compose
docker-compose up

# Test with multiple instances (horizontal scaling)
docker-compose --profile scaling up
```

## Deployment

### Pre-deployment Checklist

- [ ] All tests passing
- [ ] Code coverage >80%
- [ ] Updated documentation
- [ ] Updated CHANGELOG (if exists)
- [ ] Version bumped (if applicable)
- [ ] Tested locally with Docker
- [ ] Tested on development cluster

### Deployment Process

1. **Build and push image**:
```bash
docker build -f Dockerfile -t quay.io/your-org/slack-worker:v1.0.0 ..
docker push quay.io/your-org/slack-worker:v1.0.0
```

2. **Update Kubernetes manifests**:
```bash
# Update image tag in k8s/deployment.yaml
# Apply changes
kubectl apply -f k8s/deployment.yaml
```

3. **Verify deployment**:
```bash
kubectl get pods -n ocp-sustaining-bot
kubectl logs -f deployment/slack-worker -n ocp-sustaining-bot
```

## Debugging

### View Logs

```bash
# Docker
docker logs -f slack-worker

# Kubernetes
kubectl logs -f deployment/slack-worker -n ocp-sustaining-bot

# Specific pod
kubectl logs -f slack-worker-abc123-xyz -n ocp-sustaining-bot
```

### Common Issues

**Jobs not executing:**
- Check cron expression syntax
- Verify job is enabled in config
- Check timezone settings
- Review scheduler logs

**Lock contention:**
- Verify shared PVC is mounted
- Check lock timeout settings
- Review lock file permissions

**Slack API errors:**
- Verify bot token is valid
- Check bot permissions
- Verify channel IDs are correct

## Pull Request Process

1. Create feature branch from `main`
2. Make changes with clear commit messages
3. Add/update tests
4. Update documentation
5. Run tests locally
6. Submit PR with description
7. Address review comments
8. Merge after approval

## Code Review Checklist

- [ ] Code follows style guide
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No sensitive data in code
- [ ] Error handling implemented
- [ ] Logging added appropriately
- [ ] Configuration documented
- [ ] Backward compatible (if applicable)

## Questions?

Contact the OCP Sustaining team or open an issue.

