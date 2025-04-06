"""
Enum definitions for the API.
"""
from enum import Enum


class ResponseStatus(str, Enum):
    """Enum for API response statuses."""
    SUCCESS = "success"
    ERROR = "error" 