import logging
import traceback
import datetime
import os
import json
import sys
import pytz
import functools
from typing import Dict, Any, Optional, List, Tuple, Callable

# Set timezone - same as bot.py
TIMEZONE = pytz.timezone('Asia/Kolkata')  # Indian Standard Time (IST)

# Configure regular file logger
error_logger = logging.getLogger('error_logger')
error_logger.setLevel(logging.ERROR)
error_handler = logging.FileHandler('error_logs.log')
error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)

# Configure a separate detailed JSON error logger
detailed_logger = logging.getLogger('detailed_error_logger')
detailed_logger.setLevel(logging.ERROR)

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

class ErrorRecorder:
    """Class to handle recording, storing, and analyzing errors"""
    
    def __init__(self):
        self.errors_recorded = 0
        self.error_stats: Dict[str, int] = {}  # Count errors by type
        self.recent_errors: List[Dict[str, Any]] = []  # Store recent error details
        self.max_recent_errors = 100  # Keep only the 100 most recent errors in memory
        
        # Try to load error stats if they exist
        self._load_error_stats()
    
    def log_error(self, 
                  error: Exception, 
                  location: str, 
                  user_id: Optional[int] = None,
                  additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error with details
        
        Args:
            error: The exception object
            location: Where the error occurred (function/method name)
            user_id: User ID associated with the error (if applicable)
            additional_data: Any additional context data for the error
        """
        error_type = type(error).__name__
        timestamp = datetime.datetime.now(TIMEZONE)
        
        # Get full traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # Log to regular log file
        error_logger.error(f"Error in {location}: {str(error)}")
        
        # Create detailed error record
        error_record = {
            "timestamp": timestamp.isoformat(),
            "error_type": error_type,
            "error_message": str(error),
            "location": location,
            "stack_trace": stack_trace,
            "user_id": user_id
        }
        
        # Add any additional context data
        if additional_data:
            error_record["additional_data"] = additional_data
            
        # Save to JSON file with date-based organization
        self._save_error_to_json(error_record)
        
        # Update error statistics
        self._update_error_stats(error_type)
        
        # Update recent errors list
        self._add_to_recent_errors(error_record)
        
        # Increment counter
        self.errors_recorded += 1
        
        return error_record
    
    def _save_error_to_json(self, error_record: Dict[str, Any]) -> None:
        """Save error to JSON file organized by date"""
        # Get date for file organization
        error_date = datetime.datetime.fromisoformat(error_record["timestamp"]).strftime("%Y-%m-%d")
        error_file = f"logs/errors_{error_date}.json"
        
        try:
            # Load existing errors for today if file exists
            if os.path.exists(error_file):
                with open(error_file, 'r') as f:
                    try:
                        errors = json.load(f)
                    except json.JSONDecodeError:
                        # File exists but is corrupt/empty
                        errors = {"errors": []}
            else:
                # Create new file
                errors = {"errors": []}
            
            # Add new error
            errors["errors"].append(error_record)
            
            # Save back to file
            with open(error_file, 'w') as f:
                json.dump(errors, f, indent=2)
                
        except Exception as e:
            # Log failure to save error record
            error_logger.error(f"Failed to save error record: {e}")
    
    def _update_error_stats(self, error_type: str) -> None:
        """Update error statistics and save them"""
        # Increment counter for this error type
        if error_type in self.error_stats:
            self.error_stats[error_type] += 1
        else:
            self.error_stats[error_type] = 1
        
        # Save stats to file
        try:
            with open('logs/error_stats.json', 'w') as f:
                json.dump({
                    "total_errors": self.errors_recorded + 1,  # +1 because we haven't incremented yet
                    "error_types": self.error_stats,
                    "updated_at": datetime.datetime.now(TIMEZONE).isoformat()
                }, f, indent=2)
        except Exception as e:
            error_logger.error(f"Failed to save error stats: {e}")
    
    def _load_error_stats(self) -> None:
        """Load error statistics from file if it exists"""
        if os.path.exists('logs/error_stats.json'):
            try:
                with open('logs/error_stats.json', 'r') as f:
                    stats = json.load(f)
                    self.errors_recorded = stats.get("total_errors", 0)
                    self.error_stats = stats.get("error_types", {})
            except Exception as e:
                error_logger.error(f"Failed to load error stats: {e}")
    
    def _add_to_recent_errors(self, error_record: Dict[str, Any]) -> None:
        """Add error to recent errors list, maintaining max size"""
        self.recent_errors.append(error_record)
        
        # Trim list if it exceeds max size
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors = self.recent_errors[-self.max_recent_errors:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error statistics"""
        return {
            "total_errors": self.errors_recorded,
            "error_types": self.error_stats,
            "recent_errors": len(self.recent_errors),
            "most_common_error": max(self.error_stats.items(), key=lambda x: x[1]) if self.error_stats else None
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent errors"""
        return self.recent_errors[-limit:] if self.recent_errors else []
    
    def get_errors_by_type(self, error_type: str) -> List[Dict[str, Any]]:
        """Get errors of specific type from recent errors"""
        return [e for e in self.recent_errors if e["error_type"] == error_type]
    
    def get_errors_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Get errors from a specific date (YYYY-MM-DD)"""
        error_file = f"logs/errors_{date_str}.json"
        
        if os.path.exists(error_file):
            try:
                with open(error_file, 'r') as f:
                    errors = json.load(f)
                    return errors.get("errors", [])
            except Exception as e:
                error_logger.error(f"Failed to read errors for date {date_str}: {e}")
                return []
        return []
    
    def get_available_dates(self) -> List[str]:
        """Get list of dates for which error logs exist"""
        dates = []
        for filename in os.listdir('logs'):
            if filename.startswith('errors_') and filename.endswith('.json'):
                date_str = filename[7:-5]  # Extract YYYY-MM-DD from errors_YYYY-MM-DD.json
                dates.append(date_str)
        return sorted(dates, reverse=True)

# Create a singleton instance
error_recorder = ErrorRecorder()

def log_exception(location: str, user_id: Optional[int] = None, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Log an exception that has already occurred
    
    Args:
        location: Function name or location where error occurred
        user_id: User ID if applicable
        additional_data: Any additional context data
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_type:
        return error_recorder.log_error(
            error=exc_value,
            location=location,
            user_id=user_id,
            additional_data=additional_data
        )
    return {}

def error_handler(func=None, *args, **kwargs):
    """
    Decorator to catch and log exceptions
    
    Usage:
        @error_handler
        def my_function():
            # function code
            
        @error_handler("Custom location name", False)  # location, reraise
        def another_function():
            # function code
    """
    # Handle the case when called as @error_handler("location", False)
    if func is None or isinstance(func, str):
        # Get location and reraise parameters
        location = func if isinstance(func, str) else None
        reraise = args[0] if args and isinstance(func, str) else True
        
        # Create the actual decorator
        def decorator(f):
            @functools.wraps(f)
            def wrapper(*f_args, **f_kwargs):
                # Use the provided location or function name
                func_location = location or f.__qualname__
                
                try:
                    return f(*f_args, **f_kwargs)
                except Exception as e:
                    # Try to extract user_id if first arg is Update
                    user_id = None
                    if f_args and hasattr(f_args[0], 'effective_user') and hasattr(f_args[0].effective_user, 'id'):
                        user_id = f_args[0].effective_user.id
                    
                    # Log the error
                    error_recorder.log_error(
                        error=e,
                        location=func_location,
                        user_id=user_id,
                        additional_data={"args": str(f_args), "kwargs": str(f_kwargs)}
                    )
                    
                    # Re-raise if specified
                    if reraise:
                        raise
                    
                    # Return None if we're swallowing the exception
                    return None
            
            return wrapper
        
        # If called with string, return decorator function
        if isinstance(func, str):
            return decorator
        # If called without arguments, apply decorator to the function
        else:
            return decorator
    
    # When called as @error_handler (no arguments)
    @functools.wraps(func)
    def wrapper(*f_args, **f_kwargs):
        try:
            return func(*f_args, **f_kwargs)
        except Exception as e:
            # Try to extract user_id if first arg is Update
            user_id = None
            if f_args and hasattr(f_args[0], 'effective_user') and hasattr(f_args[0].effective_user, 'id'):
                user_id = f_args[0].effective_user.id
            
            # Log the error
            error_recorder.log_error(
                error=e,
                location=func.__qualname__,
                user_id=user_id,
                additional_data={"args": str(f_args), "kwargs": str(f_kwargs)}
            )
            
            # Re-raise by default
            raise
    
    return wrapper 