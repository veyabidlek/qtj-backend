class AppException(Exception):
    def __init__(self, error: str, message: str, status_code: int = 400, details: dict = None):
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class TelemetryValidationError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__("telemetry_validation_error", message, 400, details)


class HealthConfigError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__("health_config_error", message, 500, details)


class ThresholdNotFoundError(AppException):
    def __init__(self, parameter: str):
        super().__init__("threshold_not_found", f"Threshold for '{parameter}' not found", 404)
