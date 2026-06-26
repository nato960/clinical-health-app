
class AppException(Exception):
    """Base para todas as exceções da aplicação"""

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
        