"""
Tests for Slack client
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from slack_sdk.errors import SlackApiError
from slack_worker.slack_client import SlackClient


class TestSlackClient:
    """Test Slack client wrapper"""
    
    @patch('slack_worker.slack_client.WebClient')
    def test_send_message_success(self, mock_webclient_class, mock_config):
        """Test successful message sending"""
        with patch('slack_worker.slack_client.config', mock_config):
            mock_client = Mock()
            mock_client.chat_postMessage.return_value = {'ok': True}
            mock_webclient_class.return_value = mock_client
            
            client = SlackClient()
            result = client.send_message(channel='C12345', text='Test message')
            
            assert result is True
            mock_client.chat_postMessage.assert_called_once()
    
    @patch('slack_worker.slack_client.WebClient')
    def test_send_message_failure(self, mock_webclient_class, mock_config):
        """Test failed message sending"""
        with patch('slack_worker.slack_client.config', mock_config):
            mock_client = Mock()
            mock_client.chat_postMessage.return_value = {'ok': False}
            mock_webclient_class.return_value = mock_client
            
            client = SlackClient()
            result = client.send_message(channel='C12345', text='Test message')
            
            assert result is False
    
    @patch('slack_worker.slack_client.WebClient')
    def test_send_message_api_error(self, mock_webclient_class, mock_config):
        """Test message sending with API error"""
        with patch('slack_worker.slack_client.config', mock_config):
            mock_client = Mock()
            
            # Create a proper SlackApiError
            error_response = {'error': 'channel_not_found'}
            mock_client.chat_postMessage.side_effect = SlackApiError(
                message="Error",
                response=error_response
            )
            mock_webclient_class.return_value = mock_client
            
            client = SlackClient()
            result = client.send_message(channel='INVALID', text='Test')
            
            assert result is False
    
    @patch('slack_worker.slack_client.WebClient')
    def test_send_dm_success(self, mock_webclient_class, mock_config):
        """Test successful DM sending"""
        with patch('slack_worker.slack_client.config', mock_config):
            mock_client = Mock()
            mock_client.conversations_open.return_value = {
                'ok': True,
                'channel': {'id': 'D12345'}
            }
            mock_client.chat_postMessage.return_value = {'ok': True}
            mock_webclient_class.return_value = mock_client
            
            client = SlackClient()
            result = client.send_dm(user_id='U12345', text='Test DM')
            
            assert result is True
            mock_client.conversations_open.assert_called_once_with(users=['U12345'])
            mock_client.chat_postMessage.assert_called_once()
    
    @patch('slack_worker.slack_client.WebClient')
    def test_send_dm_channel_open_failure(self, mock_webclient_class, mock_config):
        """Test DM sending when channel open fails"""
        with patch('slack_worker.slack_client.config', mock_config):
            mock_client = Mock()
            mock_client.conversations_open.return_value = {'ok': False}
            mock_webclient_class.return_value = mock_client
            
            client = SlackClient()
            result = client.send_dm(user_id='U12345', text='Test DM')
            
            assert result is False
    
    @patch('slack_worker.slack_client.WebClient')
    def test_get_user_info_success(self, mock_webclient_class, mock_config):
        """Test getting user info"""
        with patch('slack_worker.slack_client.config', mock_config):
            mock_client = Mock()
            mock_client.users_info.return_value = {
                'ok': True,
                'user': {'id': 'U12345', 'name': 'testuser'}
            }
            mock_webclient_class.return_value = mock_client
            
            client = SlackClient()
            user_info = client.get_user_info('U12345')
            
            assert user_info['id'] == 'U12345'
            assert user_info['name'] == 'testuser'
    
    @patch('slack_worker.slack_client.WebClient')
    def test_get_user_info_failure(self, mock_webclient_class, mock_config):
        """Test getting user info failure"""
        with patch('slack_worker.slack_client.config', mock_config):
            mock_client = Mock()
            mock_client.users_info.return_value = {'ok': False}
            mock_webclient_class.return_value = mock_client
            
            client = SlackClient()
            user_info = client.get_user_info('INVALID')
            
            assert user_info == {}

