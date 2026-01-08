"""
Unit tests for scheduler
"""

import pytest
from backend.core.scheduler import (
    validate_cron_expression,
    add_job,
    remove_job,
    get_jobs,
    scheduler,
)


class TestCronValidation:
    """Tests for cron expression validation"""

    def test_valid_daily_cron(self):
        """Test valid daily cron expression"""
        assert validate_cron_expression("0 9 * * *") is True

    def test_valid_weekly_cron(self):
        """Test valid weekly cron expression"""
        assert validate_cron_expression("0 9 * * 1") is True

    def test_valid_hourly_cron(self):
        """Test valid hourly cron expression"""
        assert validate_cron_expression("0 * * * *") is True

    def test_invalid_cron_too_few_parts(self):
        """Test invalid cron with too few parts"""
        assert validate_cron_expression("0 9 * *") is False

    def test_invalid_cron_too_many_parts(self):
        """Test invalid cron with too many parts"""
        assert validate_cron_expression("0 9 * * * *") is False

    def test_invalid_cron_parts(self):
        """Test invalid cron with invalid parts"""
        assert validate_cron_expression("invalid * * * *") is False
        assert validate_cron_expression("60 * * * *") is False  # Minute 60 is invalid


class TestJobManagement:
    """Tests for job management"""

    def test_add_job_success(self):
        """Test adding a valid job"""

        def dummy_job():
            pass

        job_id = add_job(1, "test_folder", "0 9 * * *", dummy_job)
        assert job_id is not None
        assert job_id == "folder_1_test_folder"

        # Clean up
        remove_job(1, "test_folder")

    def test_add_job_invalid_cron(self):
        """Test that adding job with invalid cron fails"""

        def dummy_job():
            pass

        job_id = add_job(1, "test_folder", "invalid", dummy_job)
        assert job_id is None

    def test_remove_job(self):
        """Test removing a job"""

        def dummy_job():
            pass

        # Add job first
        add_job(1, "test_folder", "0 9 * * *", dummy_job)

        # Remove job
        remove_job(1, "test_folder")

        # Verify job is removed
        jobs = get_jobs()
        assert not any(job["id"] == "folder_1_test_folder" for job in jobs)

    def test_get_jobs(self):
        """Test getting all jobs"""

        def dummy_job():
            pass

        # Add multiple jobs
        add_job(1, "folder1", "0 9 * * *", dummy_job)
        add_job(2, "folder2", "0 10 * * *", dummy_job)

        # Get jobs
        jobs = get_jobs()
        assert len(jobs) >= 2

        # Clean up
        remove_job(1, "folder1")
        remove_job(2, "folder2")
