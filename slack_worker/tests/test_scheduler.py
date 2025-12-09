"""
Tests for job scheduler and file locking
"""

import pytest
import time
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from slack_worker.scheduler import FileLock, with_lock, JobScheduler


class TestFileLock:
    """Test file-based locking mechanism"""
    
    def test_lock_acquire_and_release(self, tmp_path):
        """Test basic lock acquisition and release"""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()
        
        with patch('slack_worker.scheduler.config') as mock_config:
            mock_config.LOCK_DIR = str(lock_dir)
            mock_config.LOCK_TIMEOUT = 5
            
            lock_name = "test_lock"
            
            with FileLock(lock_name) as lock:
                assert lock.lock_file is not None
                lock_file_path = lock_dir / f"{lock_name}.lock"
                assert lock_file_path.exists()
            
            # Lock should be released after exiting context
            assert not lock.lock_file or lock.lock_file.closed
    
    def test_lock_timeout(self, tmp_path):
        """Test lock timeout when another process holds the lock"""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()
        
        with patch('slack_worker.scheduler.config') as mock_config:
            mock_config.LOCK_DIR = str(lock_dir)
            mock_config.LOCK_TIMEOUT = 1  # Short timeout for testing
            
            lock_name = "test_lock"
            
            # Acquire lock in first context
            lock1 = FileLock(lock_name)
            lock1.__enter__()
            
            try:
                # Try to acquire same lock in second context (should timeout)
                with pytest.raises(TimeoutError):
                    with FileLock(lock_name):
                        pass
            finally:
                # Release first lock
                lock1.__exit__(None, None, None)
    
    def test_with_lock_decorator(self, tmp_path):
        """Test the with_lock decorator"""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()
        
        with patch('slack_worker.scheduler.config') as mock_config:
            mock_config.LOCK_DIR = str(lock_dir)
            mock_config.LOCK_TIMEOUT = 5
            
            call_count = [0]
            
            @with_lock("decorator_test")
            def test_function():
                call_count[0] += 1
                return "success"
            
            result = test_function()
            assert result == "success"
            assert call_count[0] == 1


class TestJobScheduler:
    """Test job scheduler"""
    
    def test_scheduler_initialization(self):
        """Test scheduler initialization"""
        scheduler = JobScheduler(timezone="UTC")
        assert scheduler.timezone == "UTC"
        assert scheduler.scheduler is not None
    
    def test_add_cron_job(self):
        """Test adding a cron job"""
        scheduler = JobScheduler(timezone="UTC")
        
        def test_job():
            return "job executed"
        
        scheduler.add_cron_job(
            func=test_job,
            job_id="test_cron_job",
            cron_expression="0 9 * * MON",
            use_lock=False  # Disable lock for simple test
        )
        
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "test_cron_job"
    
    def test_add_interval_job(self):
        """Test adding an interval job"""
        scheduler = JobScheduler(timezone="UTC")
        
        def test_job():
            return "job executed"
        
        scheduler.add_interval_job(
            func=test_job,
            job_id="test_interval_job",
            minutes=5,
            use_lock=False
        )
        
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "test_interval_job"
    
    def test_list_jobs(self):
        """Test listing scheduled jobs"""
        scheduler = JobScheduler(timezone="UTC")
        
        def job1():
            pass
        
        def job2():
            pass
        
        scheduler.add_interval_job(job1, "job1", minutes=1, use_lock=False)
        scheduler.add_interval_job(job2, "job2", minutes=2, use_lock=False)
        
        job_list = scheduler.list_jobs()
        assert len(job_list) == 2
        assert any(j['id'] == 'job1' for j in job_list)
        assert any(j['id'] == 'job2' for j in job_list)

