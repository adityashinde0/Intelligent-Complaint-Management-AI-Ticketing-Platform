from fastapi import HTTPException, status

class DomainException(Exception):
    def __init__(self, title: str, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.title = title
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)

class EntityNotFoundException(DomainException):
    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            title="Entity Not Found",
            detail=f"{entity_name} with identifier '{entity_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )

class ConflictException(DomainException):
    def __init__(self, message: str = "Concurrent modification conflict detected."):
        super().__init__(
            title="Optimistic Concurrency Conflict",
            detail=message,
            status_code=status.HTTP_409_CONFLICT
        )

class PolicyViolationException(DomainException):
    def __init__(self, message: str):
        super().__init__(
            title="Policy Violation",
            detail=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class InsufficientConfidenceException(DomainException):
    def __init__(self, message: str):
        super().__init__(
            title="Insufficient Confidence",
            detail=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
