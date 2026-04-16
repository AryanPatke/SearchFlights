"""Fare collector adapters."""

from .base import BaseCollector
from .google_flights import GoogleFlightsCollector

__all__ = ["BaseCollector", "GoogleFlightsCollector"]
