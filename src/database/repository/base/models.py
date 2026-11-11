from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class BaseModelIdentifiable(BaseModel):
    id: UUID | None = None

    @property
    def identifier(self) -> UUID:
        """
        The id of a persisted entity.

        ``id`` is optional because a model is also the input to ``create()``, where the database
        assigns it. Anything read back from the database has one, so services that need the id
        use this property instead of narrowing ``id`` at every call site.
        """
        if self.id is None:
            msg = f'{type(self).__name__} has no id yet, it was not persisted'
            raise ValueError(msg)

        return self.id


class PydanticToORMModelMixin(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedModelMixin(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
