class AppException(Exception):
    """Base for all exception in the application"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)

class NotFoundException(AppException):
    def __init__(self, message: str = "Not found"):
        super().__init__(status_code=404, message=message)

class ConflictException(AppException):
    def __init__(self, message: str = "Already exists"):
        super().__init__(status_code=409, message=message)

class BusinessException(AppException):
    def __init__(self, message: str):
        super().__init__(status_code=400, message=message)
        

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Invalid or expired authentication token"):
        super().__init__(status_code=401, message=message)

class ForbiddenException():
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(status_code=403, message=message)