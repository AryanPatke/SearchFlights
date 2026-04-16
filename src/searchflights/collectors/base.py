"""Abstract base class for fare collectors."""

from __future__ import annotations

import abc

from ..models import Fare, SearchLeg


class BaseCollector(abc.ABC):
    """Interface that every fare-data source must implement."""

    @abc.abstractmethod
    async def collect(self, leg: SearchLeg) -> list[Fare]:
        """Fetch fare options for a single search leg.

        Returns an empty list when no results are found or the source is
        unavailable for this leg.
        """

    async def setup(self) -> None:
        """Optional one-time initialisation (e.g. launch a browser)."""

    async def teardown(self) -> None:
        """Optional cleanup (e.g. close a browser)."""

    async def __aenter__(self) -> "BaseCollector":
        await self.setup()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.teardown()
