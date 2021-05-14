class CorruptFileError(IOError):
    """Raise if video cannot be opened for image retrieval."""


class NoEventsError(ValueError):
    """Raise if event query did not retrieve any results"""


class NoDetectionsError(ValueError):
    """Raise if detections query did not retrieve any results"""


class MultipleEventsError(ValueError):
    """Raise if event query retrieve multiple results"""
