"""
Smartsheet client for reading release data
Refactored from the original smartsheet.py for use in the worker service
"""

import smartsheet
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_week_range(date):
    """
    Get the start (Monday) and end (Sunday) of the week for a given date
    """
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start, end


def get_smartsheet_releases(access_token: str, sheet_id: str) -> list:
    """
    Fetch release version, start date, and end date from Smartsheet
    Filter for current week and next week only
    
    Args:
        access_token: Smartsheet API access token
        sheet_id: Smartsheet sheet ID
    
    Returns:
        List of release dictionaries with keys: release_version, start_date, end_date
    """
    try:
        # Initialize Smartsheet client
        smartsheet_client = smartsheet.Smartsheet(access_token)
        smartsheet_client.errors_as_exceptions(True)
        
        # Get the sheet
        sheet = smartsheet_client.Sheets.get_sheet(sheet_id)
        
        # Extract column names and find target columns
        columns = {col.id: col.title for col in sheet.columns}
        
        logger.debug(f"Smartsheet columns: {list(columns.values())}")
        
        # Get current date and week ranges
        today = datetime.now().date()
        current_week_start, current_week_end = get_week_range(today)
        next_week_start = current_week_start + timedelta(days=7)
        next_week_end = current_week_end + timedelta(days=7)
        
        logger.info(f"Today: {today}")
        logger.info(f"Current Week: {current_week_start} to {current_week_end}")
        logger.info(f"Next Week: {next_week_start} to {next_week_end}")
        
        # Extract row data
        releases = []
        rows_processed = 0
        
        for row in sheet.rows:
            # Skip row if all cells are empty
            if all(
                (getattr(cell, "display_value", None) in [None, ""] and 
                 getattr(cell, "value", None) in [None, ""])
                for cell in row.cells
            ):
                continue
            
            rows_processed += 1
            row_data = {}
            
            for cell in row.cells:
                column_name = columns[cell.column_id].lower()
                
                # Look for release version, start date, and end date columns
                if 'release' in column_name or 'version' in column_name:
                    row_data['release_version'] = cell.display_value if cell.display_value else cell.value
                    row_data['release_column'] = columns[cell.column_id]
                elif 'start' in column_name and 'date' in column_name:
                    row_data['start_date'] = cell.value
                    row_data['start_column'] = columns[cell.column_id]
                elif 'end' in column_name and 'date' in column_name:
                    row_data['end_date'] = cell.value
                    row_data['end_column'] = columns[cell.column_id]
            
            # Only process rows that have all required fields
            if all(key in row_data for key in ['release_version', 'start_date', 'end_date']):
                try:
                    # Parse dates - handle different date formats
                    if isinstance(row_data['start_date'], str):
                        # Try different date formats
                        for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                start_date = datetime.strptime(row_data['start_date'], date_format).date()
                                break
                            except ValueError:
                                continue
                        else:
                            logger.warning(f"Could not parse start_date: {row_data['start_date']}")
                            continue
                    else:
                        start_date = row_data['start_date']
                    
                    if isinstance(row_data['end_date'], str):
                        for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                end_date = datetime.strptime(row_data['end_date'], date_format).date()
                                break
                            except ValueError:
                                continue
                        else:
                            logger.warning(f"Could not parse end_date: {row_data['end_date']}")
                            continue
                    else:
                        end_date = row_data['end_date']
                    
                    # Check if the release falls in current week or next week
                    if (current_week_start <= start_date <= next_week_end) or \
                       (current_week_start <= end_date <= next_week_end) or \
                       (start_date <= current_week_start and end_date >= next_week_end):
                        releases.append({
                            'release_version': row_data['release_version'],
                            'start_date': start_date,
                            'end_date': end_date
                        })
                        logger.debug(f"Matched release: {row_data['release_version']}")
                        
                except (ValueError, TypeError) as e:
                    # Skip rows with invalid dates
                    logger.warning(f"Error processing row: {e}")
                    continue
        
        logger.info(f"Processed {rows_processed} rows, found {len(releases)} matching releases")
        return releases
        
    except smartsheet.exceptions.ApiError as e:
        logger.error(f"Smartsheet API error: {e.error.result.message if hasattr(e.error, 'result') else e}")
        raise
    except Exception as e:
        logger.error(f"Error fetching Smartsheet releases: {e}", exc_info=True)
        raise


