from typing import Optional, Dict, Any
import traceback
from datetime import datetime


class INDRAError(Exception):
    """Base exception class for all INDRA errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize INDRA error.
        
        Args:
            message: Error message
            details: Optional dictionary with additional error details
        """
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'traceback': self.traceback
        }

# Expert System Errors
class ExpertSystemError(INDRAError):
    """Base class for expert system related errors."""
    pass

class ExpertCreationError(ExpertSystemError):
    """Error creating expert instance."""
    pass

class ExpertAnalysisError(ExpertSystemError):
    """Error during expert analysis."""
    pass

class ConsultationError(ExpertSystemError):
    """Error during expert consultation."""
    pass

class PanelError(ExpertSystemError):
    """Error in expert panel operations."""
    pass

# Configuration Errors
class ConfigError(INDRAError):
    """Base class for configuration related errors."""
    pass

class ConfigValidationError(ConfigError):
    """Error validating configuration."""
    pass

class ConfigLoadError(ConfigError):
    """Error loading configuration file."""
    pass

class ConfigSaveError(ConfigError):
    """Error saving configuration file."""
    pass

class ConfigModificationError(ConfigError):
    """Error modifying configuration."""
    pass

# Purpose Parser Errors
class PurposeParserError(INDRAError):
    """Base class for purpose parser related errors."""
    pass

class PurposeExtractionError(PurposeParserError):
    """Error extracting requirements from purpose text."""
    pass

class RequirementValidationError(PurposeParserError):
    """Error validating extracted requirements."""
    pass

# AI Service Errors
class AIServiceError(INDRAError):
    """Base class for AI service related errors."""
    
    def __init__(self, message: str, service_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.service_name = service_name
        self.details['service_name'] = service_name

class APIError(AIServiceError):
    """Error communicating with AI API."""
    pass

class TokenLimitError(AIServiceError):
    """Error due to token limit exceeded."""
    pass

class ResponseParsingError(AIServiceError):
    """Error parsing AI service response."""
    pass

# CONFLUENCE Integration Errors
class CONFLUENCEError(INDRAError):
    """Base class for CONFLUENCE integration related errors."""
    pass

class ModelExecutionError(CONFLUENCEError):
    """Error executing hydrological model."""
    pass

class DataPreparationError(CONFLUENCEError):
    """Error preparing data for model execution."""
    pass

# File Operation Errors
class FileOperationError(INDRAError):
    """Base class for file operation related errors."""
    
    def __init__(self, message: str, file_path: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.file_path = file_path
        self.details['file_path'] = str(file_path)

class FileReadError(FileOperationError):
    """Error reading file."""
    pass

class FileWriteError(FileOperationError):
    """Error writing file."""
    pass

class FileNotFoundError(FileOperationError):
    """Error when required file is not found."""
    pass

# Validation Errors
class ValidationError(INDRAError):
    """Base class for validation related errors."""
    
    def __init__(self, message: str, validation_context: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.validation_context = validation_context
        self.details['validation_context'] = validation_context

class InputValidationError(ValidationError):
    """Error validating user input."""
    pass

class DataValidationError(ValidationError):
    """Error validating data."""
    pass

class ModelValidationError(ValidationError):
    """Error validating model configuration or output."""
    pass

def handle_exception(error: Exception) -> Dict[str, Any]:
    """
    Handle and format exception for logging and user feedback.
    
    Args:
        error: Exception to handle
        
    Returns:
        Formatted error information dictionary
    """
    if isinstance(error, INDRAError):
        error_info = error.to_dict()
    else:
        error_info = {
            'error_type': error.__class__.__name__,
            'message': str(error),
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc()
        }
    
    return error_info

def raise_from_response(response: Dict[str, Any], error_class: type) -> None:
    """
    Raise appropriate exception from API response.
    
    Args:
        response: API response dictionary
        error_class: Base error class to use
        
    Raises:
        Appropriate exception based on response
    """
    if 'error' in response:
        error_details = response['error']
        if isinstance(error_details, dict):
            message = error_details.get('message', 'Unknown error')
            details = error_details.get('details', {})
        else:
            message = str(error_details)
            details = {}
        
        raise error_class(message, details)