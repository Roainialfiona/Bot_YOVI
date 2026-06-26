from datetime import datetime
import pytz

# Default timezone Indonesia
TIMEZONE = pytz.timezone("Asia/Jakarta")

def get_current_time():
    """Return current datetime in Asia/Jakarta"""
    return datetime.now(TIMEZONE)

def format_timestamp():
    """Return formatted timestamp string"""
    return get_current_time().strftime("%Y-%m-%d %H:%M:%S")
