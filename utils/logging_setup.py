import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import json
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

class INDRAFormatter(logging.Formatter):
    """Custom formatter for INDRA logs with color support for console output"""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[0;36m',    # Cyan
        'INFO': '\033[0;32m',     # Green
        'WARNING': '\033[0;33m',  # Yellow
        'ERROR': '\033[0;31m',    # Red
        'CRITICAL': '\033[0;37;41m'  # White on Red
    }
    RESET = '\033[0m'
    
    def __init__(self, is_console: bool = False):
        """
        Initialize formatter with color support option.
        
        Args:
            is_console: Whether this formatter is for console output
        """
        super().__init__(
            fmt='%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.is_console = is_console
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional color coding."""
        # Save original values
        orig_msg = record.msg
        orig_levelname = record.levelname
        
        # Add colors for console output
        if self.is_console:
            color = self.COLORS.get(record.levelname, '')
            if color:
                record.levelname = f"{color}{record.levelname}{self.RESET}"
                if isinstance(record.msg, str):
                    record.msg = f"{color}{record.msg}{self.RESET}"
        
        # Format the message
        formatted = super().format(record)
        
        # Restore original values
        record.msg = orig_msg
        record.levelname = orig_levelname
        
        return formatted

def setup_logging(
    name: str,
    log_dir: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    capture_warnings: bool = True
) -> logging.Logger:
    """
    Set up logging configuration for INDRA.
    
    Args:
        name: Name of the logger
        log_dir: Directory for log files. If None, uses './logs'
        console_level: Logging level for console output
        file_level: Logging level for file output
        max_bytes: Maximum size of each log file
        backup_count: Number of backup log files to keep
        capture_warnings: Whether to capture Python warnings
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Set up log directory
    if log_dir is None:
        log_dir = Path('logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create console handler with color support
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(INDRAFormatter(is_console=True))
    logger.addHandler(console_handler)
    
    # Create main log file handler (size-based rotation)
    main_log_file = log_dir / f"{name}.log"
    file_handler = RotatingFileHandler(
        main_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(INDRAFormatter(is_console=False))
    logger.addHandler(file_handler)
    
    # Create daily log file handler
    daily_log_file = log_dir / f"{name}_daily.log"
    daily_handler = TimedRotatingFileHandler(
        daily_log_file,
        when='midnight',
        interval=1,
        backupCount=30  # Keep 30 days of logs
    )
    daily_handler.setLevel(file_level)
    daily_handler.setFormatter(INDRAFormatter(is_console=False))
    logger.addHandler(daily_handler)
    
    # Create error log handler (separate file for errors and above)
    error_log_file = log_dir / f"{name}_errors.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(INDRAFormatter(is_console=False))
    logger.addHandler(error_handler)
    
    # Capture warnings from Python's warning system
    if capture_warnings:
        logging.captureWarnings(True)
        warnings_logger = logging.getLogger('py.warnings')
        warnings_logger.addHandler(console_handler)
        warnings_logger.addHandler(file_handler)
    
    # Log initial message with configuration details
    config = {
        'name': name,
        'log_dir': str(log_dir),
        'console_level': logging.getLevelName(console_level),
        'file_level': logging.getLevelName(file_level),
        'max_bytes': max_bytes,
        'backup_count': backup_count,
        'capture_warnings': capture_warnings
    }
    
    logger.info(f"Logging initialized with configuration: {json.dumps(config, indent=2)}")
    
    return logger

def get_function_logger(func):
    """
    Decorator to get a logger specific to a function.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with logging
    """
    def wrapper(*args, **kwargs):
        # Get logger name from function's module and name
        logger_name = f"{func.__module__}.{func.__name__}"
        logger = logging.getLogger(logger_name)
        
        # Log function entry
        logger.debug(f"Entering function with args: {args}, kwargs: {kwargs}")
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Log function exit
            logger.debug(f"Exiting function successfully")
            return result
            
        except Exception as e:
            # Log any errors
            logger.error(f"Error in function: {str(e)}", exc_info=True)
            raise
    
    return wrapper

def log_execution_time(logger: logging.Logger):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Logger instance to use
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                elapsed_time = datetime.now() - start_time
                logger.info(f"Function {func.__name__} executed in {elapsed_time}")
                return result
            except Exception as e:
                elapsed_time = datetime.now() - start_time
                logger.error(
                    f"Function {func.__name__} failed after {elapsed_time}: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator