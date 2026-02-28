"""Abstract repository interface for data access."""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class AbstractRepository(ABC, Generic[ModelType]):
    """Abstract base repository defining the data access interface.

    All concrete repositories must implement these methods, ensuring
    a consistent API regardless of the underlying storage mechanism.
    """

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        raise NotImplementedError

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, obj: ModelType) -> ModelType:
        raise NotImplementedError

    @abstractmethod
    async def update(self, obj: ModelType) -> ModelType:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        raise NotImplementedError


class SQLAlchemyRepository(AbstractRepository[ModelType]):
    """SQLAlchemy implementation of the repository interface."""

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self._session = session
        self._model = model

    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        return await self._session.get(self._model, id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self._model).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: ModelType) -> ModelType:
        await self._session.merge(obj)
        await self._session.flush()
        return obj

    async def delete(self, id: UUID) -> bool:
        obj = await self.get_by_id(id)
        if obj is None:
            return False
        await self._session.delete(obj)
        await self._session.flush()
        return True
