from typing import Self


class InsufficientPermissionError(Exception):
    def __init__(self, message="Insufficient permission", *args, **kwargs) -> Self:
        super().__init__(message, *args, **kwargs)
