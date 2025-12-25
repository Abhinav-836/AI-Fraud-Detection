from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Union
import traceback
from .logger import get_logger

logger = get_logger(__name__)


class FraudDetectionException(Exception):
    """Base exception for fraud detection system"""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code or "FRAUD_DETECTION_ERROR"
        super().__init__(self.message)


class ModelNotFoundError(FraudDetectionException):
    """Raised when model is not found"""
    
    def __init__(self, message: str = "Model not found"):
        super().__init__(message, "MODEL_NOT_FOUND")


class ModelLoadError(FraudDetectionException):
    """Raised when model fails to load"""
    
    def __init__(self, message: str = "Failed to load model"):
        super().__init__(message, "MODEL_LOAD_ERROR")


class DataValidationError(FraudDetectionException):
    """Raised when data validation fails"""
    
    def __init__(self, message: str = "Data validation failed"):
        super().__init__(message, "DATA_VALIDATION_ERROR")


class PredictionError(FraudDetectionException):
    """Raised when prediction fails"""
    
    def __init__(self, message: str = "Prediction failed"):
        super().__init__(message, "PREDICTION_ERROR")


class StreamingError(FraudDetectionException):
    """Raised when streaming operation fails"""
    
    def __init__(self, message: str = "Streaming operation failed"):
        super().__init__(message, "STREAMING_ERROR")


async def fraud_detection_exception_handler(
    request: Request, 
    exc: FraudDetectionException
) -> JSONResponse:
    """Handle custom fraud detection exceptions"""
    
    logger.error(
        f"Fraud detection error: {exc.error_code} - {exc.message}",
        extra={'path': str(request.url)}
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "path": str(request.url)
            }
        }
    )


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors"""
    
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={'path': str(request.url)}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
                "path": str(request.url)
            }
        }
    )


async def general_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    """Handle general exceptions"""
    
    error_trace = traceback.format_exc()
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            'path': str(request.url),
            'trace': error_trace
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "path": str(request.url)
            }
        }
    )


def setup_exception_handlers(app):
    """Setup all exception handlers for the FastAPI app"""
    
    app.add_exception_handler(
        FraudDetectionException, 
        fraud_detection_exception_handler
    )
    
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler
    )
    
    app.add_exception_handler(
        Exception,
        general_exception_handler
    )
    
    logger.info("Exception handlers configured")


class ErrorResponse:
    """Standardized error response builder"""
    
    @staticmethod
    def build(
        code: str,
        message: str,
        details: Union[dict, list, None] = None,
        status_code: int = 500
    ) -> JSONResponse:
        """
        Build standardized error response
        
        Args:
            code: Error code
            message: Error message
            details: Additional error details
            status_code: HTTP status code
            
        Returns:
            JSONResponse with error details
        """
        content = {
            "error": {
                "code": code,
                "message": message
            }
        }
        
        if details:
            content["error"]["details"] = details
        
        return JSONResponse(
            status_code=status_code,
            content=content
        )
    
    @staticmethod
    def not_found(message: str = "Resource not found") -> JSONResponse:
        """404 Not Found response"""
        return ErrorResponse.build(
            "NOT_FOUND",
            message,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def bad_request(message: str = "Bad request", details=None) -> JSONResponse:
        """400 Bad Request response"""
        return ErrorResponse.build(
            "BAD_REQUEST",
            message,
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> JSONResponse:
        """401 Unauthorized response"""
        return ErrorResponse.build(
            "UNAUTHORIZED",
            message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(message: str = "Forbidden") -> JSONResponse:
        """403 Forbidden response"""
        return ErrorResponse.build(
            "FORBIDDEN",
            message,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def internal_error(message: str = "Internal server error") -> JSONResponse:
        """500 Internal Server Error response"""
        return ErrorResponse.build(
            "INTERNAL_ERROR",
            message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    @staticmethod
    def service_unavailable(message: str = "Service unavailable") -> JSONResponse:
        """503 Service Unavailable response"""
        return ErrorResponse.build(
            "SERVICE_UNAVAILABLE",
            message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )