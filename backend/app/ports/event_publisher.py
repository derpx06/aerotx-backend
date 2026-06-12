from typing import Protocol

from app.domain.events import DomainEvent


class DomainEventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None:
        raise NotImplementedError
