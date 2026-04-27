from abc import ABC, abstractmethod
from typing import Any


class ServiceError(Exception):
    pass


class BaseService(ABC):

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize client / connection."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the service is reachable."""
        pass
