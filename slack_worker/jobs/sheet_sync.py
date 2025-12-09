"""
Smartsheet to Google Sheets synchronization job

Why You Need It
Historical Record - Keeps history of what releases were scheduled when
Reference - Team can see Smartsheet data in Google Sheets (easier to access)
Audit Trail - Timestamp shows when data was last synced
Metadata - Adds Leads/Members (from env vars) that aren't in Smartsheet
Backup - If Smartsheet changes, you have a record in Google Sheets

"""

import logging
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from slack_worker.smartsheet_client.smartsheet_reader import get_smartsheet_releases
from sdk.gsheet.gsheet import GSheet
from slack_worker.config import config
import gspread

logger = logging.getLogger(__name__)


class SheetSyncManager:
    """Manager for synchronizing Smartsheet data to Google Sheets"""
    
    def __init__(self):
        """Initialize the sheet sync manager"""
        self.gsheet_client = gspread.service_account_from_dict(config.ROTA_SERVICE_ACCOUNT)
        self.rota_sheet = self.gsheet_client.open(config.ROTA_SHEET)
        
        # Get or create the sync worksheet
        try:
            self.sync_worksheet = self.rota_sheet.worksheet(config.ROTA_SYNC_WORKSHEET)
            logger.info(f"Found existing sync worksheet: {config.ROTA_SYNC_WORKSHEET}")
        except gspread.exceptions.WorksheetNotFound:
            self.sync_worksheet = self.rota_sheet.add_worksheet(
                title=config.ROTA_SYNC_WORKSHEET,
                rows=100,
                cols=10
            )
            logger.info(f"Created new sync worksheet: {config.ROTA_SYNC_WORKSHEET}")
            
            # Add headers
            headers = [
                'Release Version',
                'Start Date',
                'End Date',
                'PM',
                'Members',
                'Last Synced',
                'Source'
            ]
            self.sync_worksheet.update('A1:G1', [headers])
    
    def sync_releases(self, releases: list):
        """
        Sync release data to Google Sheets
        
        Args:
            releases: List of release dictionaries from Smartsheet
        """
        if not releases:
            logger.info("No releases to sync")
            return
        
        # Get current timestamp
        sync_timestamp = datetime.now().isoformat()
        
        # Prepare rows for update
        rows = []
        for release in releases:
            # Add leads and members from config
            leads = ', '.join(config.ROTA_LEADS) if config.ROTA_LEADS else 'TBD'
            members = ', '.join(config.ROTA_MEMBERS) if config.ROTA_MEMBERS else 'TBD'
            
            row = [
                release['release_version'],
                str(release['start_date']),
                str(release['end_date']),
                leads,
                members,
                sync_timestamp,
                'Smartsheet'
            ]
            rows.append(row)
        
        # Clear existing data (except header)
        if self.sync_worksheet.row_count > 1:
            self.sync_worksheet.batch_clear([f'A2:G{self.sync_worksheet.row_count}'])
        
        # Update with new data
        if rows:
            self.sync_worksheet.update(
                f'A2:G{len(rows) + 1}',
                rows,
                value_input_option='USER_ENTERED'
            )
            
            logger.info(f"Successfully synced {len(rows)} releases to Google Sheets")
    
    def get_sync_history(self, limit: int = 10) -> list:
        """
        Get recent sync history
        
        Args:
            limit: Number of recent entries to return
        
        Returns:
            List of recent sync records
        """
        try:
            all_values = self.sync_worksheet.get_all_values()
            
            if len(all_values) <= 1:  # Only header or empty
                return []
            
            # Skip header and get recent entries
            recent_entries = all_values[1:limit + 1]
            return recent_entries
            
        except Exception as e:
            logger.error(f"Error getting sync history: {e}")
            return []


def sync_smartsheet_to_gsheet():
    """
    Synchronize Smartsheet data to Google Sheets
    This job runs on a schedule to keep the Google Sheet updated
    """
    logger.info("Starting Smartsheet to Google Sheets sync job")
    
    try:
        # Check if we have the required configuration
        if not config.SMARTSHEET_ACCESS_TOKEN or not config.SMARTSHEET_SHEET_ID:
            logger.error(
                "Missing Smartsheet configuration (SMARTSHEET_ACCESS_TOKEN or SMARTSHEET_SHEET_ID). "
                "Skipping sync."
            )
            return
        
        # Fetch releases from Smartsheet
        logger.info("Fetching releases from Smartsheet...")
        releases = get_smartsheet_releases(
            access_token=config.SMARTSHEET_ACCESS_TOKEN,
            sheet_id=config.SMARTSHEET_SHEET_ID
        )
        
        if not releases:
            logger.warning("No releases fetched from Smartsheet")
            # Still update the sheet to mark the sync attempt
            releases = []
        
        logger.info(f"Fetched {len(releases)} release(s) from Smartsheet")
        
        # Sync to Google Sheets
        logger.info("Syncing to Google Sheets...")
        sync_manager = SheetSyncManager()
        sync_manager.sync_releases(releases)
        
        logger.info("Smartsheet sync completed successfully")
        
    except Exception as e:
        logger.error(f"Error in Smartsheet sync job: {e}", exc_info=True)
        raise


def get_week_range(date_obj):
    """
    Get the start (Monday) and end (Sunday) of the week for a given date
    
    Args:
        date_obj: Date object
    
    Returns:
        Tuple of (start_date, end_date)
    """
    start = date_obj - timedelta(days=date_obj.weekday())
    end = start + timedelta(days=6)
    return start, end


