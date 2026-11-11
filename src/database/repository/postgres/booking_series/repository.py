from src.database.models import BookingSeriesORM
from src.database.repository.postgres.base import BasePostgresRepository
from src.database.repository.postgres.base import orm_kwargs
from src.database.repository.postgres.booking_series.dtos import BookingSeries


class BookingSeriesRepository(BasePostgresRepository[BookingSeriesORM, BookingSeries]):
    _orm_class = BookingSeriesORM

    def orm_to_model(self, orm: BookingSeriesORM) -> BookingSeries:
        return BookingSeries.model_validate(orm)

    def model_to_orm(self, model: BookingSeries) -> BookingSeriesORM:
        return BookingSeriesORM(**orm_kwargs(model))
