class QuotaExceededError(Exception):
    def __init__(self, message="An exception occurred"):
        self.description = message
