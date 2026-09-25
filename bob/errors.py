class BobError(Exception):
    """Base Bob error."""


class ConfigurationError(BobError):
    pass


class IdentityMismatch(BobError):
    pass


class ProtocolError(BobError):
    pass


class AuthorityError(BobError):
    pass


class ExternalEffectError(BobError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
