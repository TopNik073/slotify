from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class APIModel(BaseModel):
    """
    Base for request and response bodies.

    The wire format is camelCase while the Python side stays snake_case, and
    ``populate_by_name`` also accepts snake_case bodies for Python callers. New clients should
    consistently use camelCase. URL query parameters declare their aliases separately in Query.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        alias_generator=to_camel,
    )
