"""
Tests for Smartsheet to Google Sheets sync job
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from slack_worker.jobs.sheet_sync import (
    SheetSyncManager,
    sync_smartsheet_to_gsheet,
    get_week_range,
)


class TestGetWeekRange:
    """Test week range calculation"""
    
    def test_get_week_range_monday(self):
        """Test week range for Monday"""
        test_date = date(2024, 1, 8)  # Monday
        start, end = get_week_range(test_date)
        
        assert start == date(2024, 1, 8)
        assert end == date(2024, 1, 14)
    
    def test_get_week_range_friday(self):
        """Test week range for Friday"""
        test_date = date(2024, 1, 12)  # Friday
        start, end = get_week_range(test_date)
        
        assert start == date(2024, 1, 8)  # Monday
        assert end == date(2024, 1, 14)   # Sunday


class TestSheetSyncManager:
    """Test sheet sync manager"""
    
    @patch('slack_worker.jobs.sheet_sync.gspread')
    def test_sync_manager_init_existing_worksheet(self, mock_gspread, mock_config):
        """Test initialization with existing worksheet"""
        with patch('slack_worker.jobs.sheet_sync.config', mock_config):
            mock_client = Mock()
            mock_sheet = Mock()
            mock_worksheet = Mock()
            
            mock_gspread.service_account_from_dict.return_value = mock_client
            mock_client.open.return_value = mock_sheet
            mock_sheet.worksheet.return_value = mock_worksheet
            
            manager = SheetSyncManager()
            
            assert manager.sync_worksheet == mock_worksheet
            mock_sheet.worksheet.assert_called_once_with('Smartsheet_Sync')
    
    @patch('slack_worker.jobs.sheet_sync.gspread')
    def test_sync_manager_init_new_worksheet(self, mock_gspread, mock_config):
        """Test initialization creating new worksheet"""
        import gspread.exceptions
        
        with patch('slack_worker.jobs.sheet_sync.config', mock_config):
            mock_client = Mock()
            mock_sheet = Mock()
            mock_worksheet = Mock()
            
            mock_gspread.service_account_from_dict.return_value = mock_client
            mock_client.open.return_value = mock_sheet
            
            # Simulate worksheet not found - use actual exception class
            mock_gspread.exceptions = gspread.exceptions
            mock_sheet.worksheet.side_effect = gspread.exceptions.WorksheetNotFound('test')
            mock_sheet.add_worksheet.return_value = mock_worksheet
            
            manager = SheetSyncManager()
            
            assert manager.sync_worksheet == mock_worksheet
            mock_sheet.add_worksheet.assert_called_once()
    
    @patch('slack_worker.jobs.sheet_sync.gspread')
    def test_sync_releases(self, mock_gspread, mock_config, sample_releases):
        """Test syncing releases to Google Sheets"""
        with patch('slack_worker.jobs.sheet_sync.config', mock_config):
            mock_client = Mock()
            mock_sheet = Mock()
            mock_worksheet = Mock()
            mock_worksheet.row_count = 10
            
            mock_gspread.service_account_from_dict.return_value = mock_client
            mock_client.open.return_value = mock_sheet
            mock_sheet.worksheet.return_value = mock_worksheet
            
            manager = SheetSyncManager()
            manager.sync_releases(sample_releases)
            
            # Should clear existing data and update with new data
            mock_worksheet.batch_clear.assert_called_once()
            mock_worksheet.update.assert_called_once()
    
    @patch('slack_worker.jobs.sheet_sync.gspread')
    def test_sync_releases_empty(self, mock_gspread, mock_config):
        """Test syncing with no releases"""
        with patch('slack_worker.jobs.sheet_sync.config', mock_config):
            mock_client = Mock()
            mock_sheet = Mock()
            mock_worksheet = Mock()
            
            mock_gspread.service_account_from_dict.return_value = mock_client
            mock_client.open.return_value = mock_sheet
            mock_sheet.worksheet.return_value = mock_worksheet
            
            manager = SheetSyncManager()
            manager.sync_releases([])
            
            # Should not call update
            mock_worksheet.update.assert_not_called()
    
    @patch('slack_worker.jobs.sheet_sync.gspread')
    def test_get_sync_history(self, mock_gspread, mock_config):
        """Test getting sync history"""
        with patch('slack_worker.jobs.sheet_sync.config', mock_config):
            mock_client = Mock()
            mock_sheet = Mock()
            mock_worksheet = Mock()
            
            # Mock data with header and entries
            mock_data = [
                ['Release', 'Start', 'End', 'Leads', 'Members', 'Synced', 'Source'],
                ['4.15.1', '2024-01-08', '2024-01-12', 'lead1', 'member1', '2024-01-01', 'Smartsheet'],
                ['4.16.2', '2024-01-15', '2024-01-19', 'lead2', 'member2', '2024-01-01', 'Smartsheet'],
            ]
            mock_worksheet.get_all_values.return_value = mock_data
            
            mock_gspread.service_account_from_dict.return_value = mock_client
            mock_client.open.return_value = mock_sheet
            mock_sheet.worksheet.return_value = mock_worksheet
            
            manager = SheetSyncManager()
            history = manager.get_sync_history(limit=5)
            
            assert len(history) == 2
            assert history[0][0] == '4.15.1'


class TestSyncSmartsheetToGsheet:
    """Test main sync job function"""
    
    @patch('slack_worker.jobs.sheet_sync.SheetSyncManager')
    @patch('slack_worker.jobs.sheet_sync.get_smartsheet_releases')
    def test_sync_smartsheet_to_gsheet_success(
        self,
        mock_get_releases,
        mock_sync_manager_class,
        mock_config,
        sample_releases
    ):
        """Test successful sync"""
        with patch('slack_worker.jobs.sheet_sync.config', mock_config):
            mock_get_releases.return_value = sample_releases
            mock_manager = Mock()
            mock_sync_manager_class.return_value = mock_manager
            
            sync_smartsheet_to_gsheet()
            
            mock_get_releases.assert_called_once_with(
                access_token='smartsheet-token',
                sheet_id='sheet-id-123'
            )
            mock_manager.sync_releases.assert_called_once_with(sample_releases)
    
    @patch('slack_worker.jobs.sheet_sync.SheetSyncManager')
    @patch('slack_worker.jobs.sheet_sync.get_smartsheet_releases')
    def test_sync_smartsheet_to_gsheet_no_releases(
        self,
        mock_get_releases,
        mock_sync_manager_class,
        mock_config
    ):
        """Test sync with no releases"""
        with patch('slack_worker.jobs.sheet_sync.config', mock_config):
            mock_get_releases.return_value = []
            mock_manager = Mock()
            mock_sync_manager_class.return_value = mock_manager
            
            sync_smartsheet_to_gsheet()
            
            mock_manager.sync_releases.assert_called_once_with([])
    
    def test_sync_smartsheet_to_gsheet_missing_config(self, mock_config):
        """Test sync with missing configuration"""
        mock_config.SMARTSHEET_ACCESS_TOKEN = ''
        mock_config.SMARTSHEET_SHEET_ID = ''
        
        with patch('slack_worker.jobs.sheet_sync.config', mock_config):
            # Should not raise exception, just log error
            sync_smartsheet_to_gsheet()
    
    @patch('slack_worker.jobs.sheet_sync.get_smartsheet_releases')
    def test_sync_smartsheet_to_gsheet_error(
        self,
        mock_get_releases,
        mock_config
    ):
        """Test sync with error"""
        with patch('slack_worker.jobs.sheet_sync.config', mock_config):
            mock_get_releases.side_effect = Exception("Test error")
            
            with pytest.raises(Exception):
                sync_smartsheet_to_gsheet()

