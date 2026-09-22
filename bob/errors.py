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
    pass
