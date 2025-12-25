import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from functools import wraps
from .logger import get_logger

logger = get_logger(__name__)


def timing_decorator(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = (end_time - start_time) * 1000  # Convert to ms
        logger.debug(f"{func.__name__} executed in {execution_time:.2f}ms")
        
        return result
    return wrapper


def retry_decorator(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry a function on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    logger.warning(f"{func.__name__} failed (attempt {retries}/{max_retries}): {str(e)}")
                    time.sleep(delay * retries)  # Exponential backoff
            
        return wrapper
    return decorator


def generate_transaction_id() -> str:
    """Generate a unique transaction ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    random_part = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    return f"TXN_{timestamp}_{random_part}"


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency"""
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥"
    }
    
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage safely"""
    if total == 0:
        return 0.0
    return (part / total) * 100


def parse_date(date_string: str) -> datetime:
    """Parse date string to datetime object"""
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y",
        "%m/%d/%Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_string}")


def get_date_range(days: int = 7) -> tuple:
    """Get date range for the last N days"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers"""
    if denominator == 0:
        return default
    return numerator / denominator


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def calculate_business_days(start_date: datetime, end_date: datetime) -> int:
    """Calculate number of business days between two dates"""
    business_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday = 0, Sunday = 6
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days


def validate_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """Mask sensitive data (e.g., credit card numbers)"""
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    masked_length = len(data) - visible_chars
    return mask_char * masked_length + data[-visible_chars:]


def calculate_hash(data: str) -> str:
    """Calculate SHA-256 hash of data"""
    return hashlib.sha256(data.encode()).hexdigest()


def pretty_print_json(data: Dict) -> str:
    """Pretty print JSON data"""
    return json.dumps(data, indent=2, sort_keys=True)


def get_time_of_day(hour: int) -> str:
    """Get time of day category from hour"""
    if 0 <= hour < 6:
        return "night"
    elif 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    else:
        return "evening"


def is_weekend(day_of_week: int) -> bool:
    """Check if day is weekend (0=Monday, 6=Sunday)"""
    return day_of_week >= 5


def calculate_age_days(date: datetime) -> int:
    """Calculate age in days from a date"""
    return (datetime.now() - date).days


def round_to_decimal_places(value: float, places: int = 2) -> float:
    """Round value to specified decimal places"""
    return round(value, places)


def convert_size_to_mb(size_bytes: int) -> float:
    """Convert bytes to megabytes"""
    return size_bytes / (1024 * 1024)


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate string to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


class Timer:
    """Context manager for timing code blocks"""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.time()
        duration = (self.end_time - self.start_time) * 1000
        logger.info(f"{self.name} completed in {duration:.2f}ms")
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in milliseconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_calls: int, time_window: int):
        """
        Initialize rate limiter
        
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def is_allowed(self) -> bool:
        """Check if a call is allowed"""
        now = time.time()
        
        # Remove old calls outside time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        # Check if we're within limits
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        
        return False
    
    def wait_time(self) -> float:
        """Get time to wait before next call is allowed"""
        if len(self.calls) < self.max_calls:
            return 0
        
        oldest_call = min(self.calls)
        return max(0, self.time_window - (time.time() - oldest_call))