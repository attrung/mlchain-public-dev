class MlChainError(Exception):
    """Base class for all exceptions."""
    pass

class SerializationError(Exception):
    """Raised when an object cannot be serialized."""