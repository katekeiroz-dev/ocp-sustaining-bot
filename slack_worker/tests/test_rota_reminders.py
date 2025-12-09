"""
Tests for ROTA reminder jobs
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from slack_worker.jobs.rota_reminders import (
    get_current_week_releases,
    get_next_week_releases,
    format_release_message,
    get_user_mention,
    send_group_reminder,
    send_dm_reminders,
)


class TestRotaReminderHelpers:
    """Test helper functions for ROTA reminders"""
    
    def test_format_release_message_empty(self):
        """Test formatting with no releases"""
        message = format_release_message([], "This Week")
        assert "No releases scheduled" in message
    
    def test_format_release_message_with_releases(self, mock_config):
        """Test formatting with releases"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            releases = [
                {
                    'version': '4.15.1',
                    'start_date': '2024-01-08',
                    'end_date': '2024-01-12',
                    'pm': 'john.doe',
                    'qe1': 'jane.smith',
                    'qe2': 'bob.wilson'
                }
            ]
            
            message = format_release_message(releases, "This Week")
            assert "4.15.1" in message
            assert "This Week" in message
            assert "2024-01-08" in message
    
    def test_get_user_mention(self, mock_config):
        """Test user mention formatting"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            # User in ROTA_USERS
            mention = get_user_mention("john.doe")
            assert mention == "<@U12345>"
            
            # User not in ROTA_USERS
            mention = get_user_mention("unknown.user")
            assert mention == "unknown.user"
            
            # TBD user
            mention = get_user_mention("TBD")
            assert mention == "TBD"


class TestGetReleases:
    """Test release fetching functions"""
    
    @patch('slack_worker.jobs.rota_reminders.GSheet')
    def test_get_current_week_releases(self, mock_gsheet_class, mock_config, sample_rota_data):
        """Test fetching current week releases"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            mock_instance = Mock()
            mock_instance.fetch_data_by_time.return_value = sample_rota_data[:1]
            mock_gsheet_class.return_value = mock_instance
            
            releases = get_current_week_releases()
            
            assert len(releases) == 1
            assert releases[0]['version'] == '4.15.1'
            mock_instance.fetch_data_by_time.assert_called_once_with("This Week")
    
    @patch('slack_worker.jobs.rota_reminders.GSheet')
    def test_get_next_week_releases(self, mock_gsheet_class, mock_config, sample_rota_data):
        """Test fetching next week releases"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            mock_instance = Mock()
            mock_instance.fetch_data_by_time.return_value = sample_rota_data[1:]
            mock_gsheet_class.return_value = mock_instance
            
            releases = get_next_week_releases()
            
            assert len(releases) == 1
            assert releases[0]['version'] == '4.16.2'
            mock_instance.fetch_data_by_time.assert_called_once_with("Next Week")
    
    @patch('slack_worker.jobs.rota_reminders.GSheet')
    def test_get_releases_error_handling(self, mock_gsheet_class, mock_config):
        """Test error handling when fetching releases"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            mock_instance = Mock()
            mock_instance.fetch_data_by_time.side_effect = Exception("Test error")
            mock_gsheet_class.return_value = mock_instance
            
            releases = get_current_week_releases()
            assert releases == []


class TestSendGroupReminder:
    """Test group reminder job"""
    
    @patch('slack_worker.jobs.rota_reminders.slack_client')
    @patch('slack_worker.jobs.rota_reminders.get_current_week_releases')
    @patch('slack_worker.jobs.rota_reminders.get_next_week_releases')
    @patch('slack_worker.jobs.rota_reminders.datetime')
    def test_send_group_reminder_monday(
        self,
        mock_datetime,
        mock_next_week,
        mock_current_week,
        mock_slack,
        mock_config,
        sample_rota_data
    ):
        """Test group reminder on Monday"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            # Mock Monday
            mock_date = Mock()
            mock_date.weekday.return_value = 0  # Monday
            mock_datetime.now.return_value.date.return_value = mock_date
            
            # Mock releases
            mock_current_week.return_value = [{
                'version': '4.15.1',
                'start_date': '2024-01-08',
                'end_date': '2024-01-12',
                'pm': 'john.doe',
                'qe1': 'jane.smith',
                'qe2': 'bob.wilson'
            }]
            mock_next_week.return_value = []
            
            send_group_reminder()
            
            # Should send message to group channel
            mock_slack.send_message.assert_called_once()
            call_args = mock_slack.send_message.call_args
            assert call_args[1]['channel'] == 'C12345'
            assert 'ROTA' in call_args[1]['text']
    
    @patch('slack_worker.jobs.rota_reminders.slack_client')
    @patch('slack_worker.jobs.rota_reminders.get_current_week_releases')
    @patch('slack_worker.jobs.rota_reminders.datetime')
    def test_send_group_reminder_thursday(
        self,
        mock_datetime,
        mock_current_week,
        mock_slack,
        mock_config
    ):
        """Test group reminder on Thursday"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            # Mock Thursday
            mock_date = Mock()
            mock_date.weekday.return_value = 3  # Thursday
            mock_datetime.now.return_value.date.return_value = mock_date
            
            mock_current_week.return_value = []
            
            send_group_reminder()
            
            # Should send mid-week reminder
            mock_slack.send_message.assert_called_once()
            call_args = mock_slack.send_message.call_args
            assert 'Mid-Week' in call_args[1]['text']


class TestSendDMReminders:
    """Test DM reminder job"""
    
    @patch('slack_worker.jobs.rota_reminders.slack_client')
    @patch('slack_worker.jobs.rota_reminders.get_current_week_releases')
    @patch('slack_worker.jobs.rota_reminders.datetime')
    def test_send_dm_reminders_monday(
        self,
        mock_datetime,
        mock_current_week,
        mock_slack,
        mock_config
    ):
        """Test DM reminders on Monday"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            # Mock Monday
            mock_date = Mock()
            mock_date.weekday.return_value = 0  # Monday
            mock_datetime.now.return_value.date.return_value = mock_date
            
            # Mock releases with users
            mock_current_week.return_value = [{
                'version': '4.15.1',
                'start_date': '2024-01-08',
                'end_date': '2024-01-12',
                'pm': 'john.doe',
                'qe1': 'jane.smith',
                'qe2': 'bob.wilson'
            }]
            
            send_dm_reminders()
            
            # Should send DMs to 3 people
            assert mock_slack.send_dm.call_count == 3
    
    @patch('slack_worker.jobs.rota_reminders.slack_client')
    @patch('slack_worker.jobs.rota_reminders.get_current_week_releases')
    @patch('slack_worker.jobs.rota_reminders.datetime')
    def test_send_dm_reminders_friday(
        self,
        mock_datetime,
        mock_current_week,
        mock_slack,
        mock_config
    ):
        """Test DM reminders on Friday"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            # Mock Friday
            mock_date = Mock()
            mock_date.weekday.return_value = 4  # Friday
            mock_datetime.now.return_value.date.return_value = mock_date
            
            mock_current_week.return_value = [{
                'version': '4.15.1',
                'start_date': '2024-01-08',
                'end_date': '2024-01-12',
                'pm': 'john.doe',
                'qe1': 'jane.smith',
                'qe2': 'bob.wilson'
            }]
            
            send_dm_reminders()
            
            # Should send DMs
            assert mock_slack.send_dm.call_count > 0
            
            # Check that message mentions "this week"
            call_args = mock_slack.send_dm.call_args
            assert 'this week' in call_args[1]['text']
    
    @patch('slack_worker.jobs.rota_reminders.slack_client')
    @patch('slack_worker.jobs.rota_reminders.get_current_week_releases')
    @patch('slack_worker.jobs.rota_reminders.datetime')
    def test_send_dm_reminders_no_releases(
        self,
        mock_datetime,
        mock_current_week,
        mock_slack,
        mock_config
    ):
        """Test DM reminders with no releases"""
        with patch('slack_worker.jobs.rota_reminders.config', mock_config):
            mock_date = Mock()
            mock_date.weekday.return_value = 0
            mock_datetime.now.return_value.date.return_value = mock_date
            
            mock_current_week.return_value = []
            
            send_dm_reminders()
            
            # Should not send any DMs
            mock_slack.send_dm.assert_not_called()

