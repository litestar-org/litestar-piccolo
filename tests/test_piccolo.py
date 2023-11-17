from __future__ import annotations

from decimal import Decimal
from typing import Callable

import pytest
from litestar import Litestar
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client
from piccolo.columns import Column, column_types
from piccolo.table import Table
from polyfactory.utils.predicates import is_annotated
from typing_extensions import get_args

from litestar_piccolo import PiccoloDTO, PiccoloPlugin
from tests.app.endpoints import (
    create_concert,
    retrieve_studio,
    retrieve_studio_plugin,
    retrieve_venues,
    retrieve_venues_plugin,
    studio,
    venues,
)
from tests.app.tables import RecordingStudio, Venue

pytestmark = pytest.mark.anyio


def test_dto_serializing_single_piccolo_table(scaffold_piccolo: Callable) -> None:
    with create_test_client(route_handlers=[retrieve_studio]) as client:
        response = client.get("/studio")
        assert response.status_code == HTTP_200_OK
        assert str(RecordingStudio(**response.json()).querystring) == str(studio.querystring)


def test_dto_serializing_multiple_piccolo_tables(scaffold_piccolo: Callable) -> None:
    with create_test_client(route_handlers=[retrieve_venues]) as client:
        response = client.get("/venues")
        assert response.status_code == HTTP_200_OK
        assert [str(Venue(**value).querystring) for value in response.json()] == [str(v.querystring) for v in venues]


def test_plugin_serializing_single_piccolo_table(scaffold_piccolo: Callable) -> None:
    with create_test_client(route_handlers=[retrieve_studio_plugin], plugins=[PiccoloPlugin()]) as client:
        response = client.get("/plugin/studio")
        assert response.status_code == HTTP_200_OK
        assert str(RecordingStudio(**response.json()).querystring) == str(studio.querystring)


def test_plugin_serializing_multiple_piccolo_tables(scaffold_piccolo: Callable) -> None:
    with create_test_client(route_handlers=[retrieve_venues_plugin], plugins=[PiccoloPlugin()]) as client:
        response = client.get("/plugin/venues")
        assert response.status_code == HTTP_200_OK
        assert [str(Venue(**value).querystring) for value in response.json()] == [str(v.querystring) for v in venues]


@pytest.mark.parametrize(
    "piccolo_type, py_type, meta_data_key",
    (
        (column_types.Decimal, Decimal, None),
        (column_types.Numeric, Decimal, None),
        (column_types.Email, str, "max_length"),
        (column_types.Varchar, str, "max_length"),
        (column_types.JSON, str, "format"),
        (column_types.JSONB, str, "format"),
        (column_types.Text, str, "format"),
    ),
)
def test_piccolo_dto_type_conversion(piccolo_type: type[Column], py_type: type, meta_data_key: str | None) -> None:
    class _Table(Table):
        field = piccolo_type(required=True, help_text="my column")

    field_defs = list(PiccoloDTO.generate_field_definitions(_Table))
    assert len(field_defs) == 2
    field_def = field_defs[1]
    assert is_annotated(field_def.raw)
    assert field_def.annotation is py_type
    metadata = get_args(field_def.raw)[1]

    assert metadata.extra.get("description", "")
    if meta_data_key:
        assert metadata.extra.get(meta_data_key, "") or getattr(metadata, meta_data_key, None)


def test_piccolo_dto_openapi_spec_generation(scaffold_piccolo: Callable) -> None:
    app = Litestar(route_handlers=[retrieve_studio, retrieve_venues, create_concert])
    schema = app.openapi_schema

    assert schema.paths
    assert len(schema.paths) == 3
    concert_path = schema.paths["/concert"]
    assert concert_path

    studio_path = schema.paths["/studio"]
    assert studio_path

    venues_path = schema.paths["/venues"]
    assert venues_path

    post_operation = concert_path.post
    assert (
        post_operation.request_body.content["application/json"].schema.ref  # type: ignore
        == "#/components/schemas/CreateConcertConcertRequestBody"
    )

    studio_path_get_operation = studio_path.get
    assert studio_path_get_operation.responses["200"].content["application/json"].schema.ref in {  # type: ignore
        "#/components/schemas/RetrieveStudioRecordingStudioResponseBody",
        "#/components/schemas/tests.app.endpoints.retrieve_studioRecordingStudioResponseBody",
    }

    venues_path_get_operation = venues_path.get
    assert venues_path_get_operation.responses["200"].content["application/json"].schema.items.ref in {  # type: ignore
        "#/components/schemas/RetrieveVenuesVenueResponseBody",
        "#/components/schemas/tests.app.endpoints.retrieve_venuesVenueResponseBody",
    }

    concert_schema = schema.components.schemas["CreateConcertConcertRequestBody"]
    assert concert_schema
    assert concert_schema.to_schema() == {
        "properties": {
            "band_1": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
            "band_2": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
            "venue": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
        },
        "required": [],
        "title": "CreateConcertConcertRequestBody",
        "type": "object",
    }

    record_studio_schema = schema.components.schemas.get(
        "RetrieveStudioRecordingStudioResponseBody",
        schema.components.schemas.get("tests.app.endpoints.retrieve_studioRecordingStudioResponseBody"),
    )
    assert record_studio_schema
    assert record_studio_schema.to_schema() in (
        {
            "properties": {
                "facilities": {"oneOf": [{"type": "null"}, {"type": "string"}]},
                "facilities_b": {"oneOf": [{"type": "null"}, {"type": "string"}]},
                "microphones": {"oneOf": [{"type": "null"}, {"items": {"type": "string"}, "type": "array"}]},
                "id": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
            },
            "required": [],
            "title": "RetrieveStudioRecordingStudioResponseBody",
            "type": "object",
        },
        {
            "properties": {
                "facilities": {"oneOf": [{"type": "null"}, {"type": "string"}]},
                "facilities_b": {"oneOf": [{"type": "null"}, {"type": "string"}]},
                "microphones": {"oneOf": [{"type": "null"}, {"items": {"type": "string"}, "type": "array"}]},
                "id": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
            },
            "required": [],
            "title": "tests.app.endpoints.retrieve_studioRecordingStudioResponseBody",
            "type": "object",
        },
    )

    venue_schema = schema.components.schemas.get(
        "RetrieveVenuesVenueResponseBody",
        schema.components.schemas.get("tests.app.endpoints.retrieve_venuesVenueResponseBody"),
    )
    assert venue_schema
    assert venue_schema.to_schema() in (
        {
            "properties": {
                "capacity": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
                "id": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
                "name": {"oneOf": [{"type": "null"}, {"type": "string"}]},
            },
            "required": [],
            "title": "RetrieveVenuesVenueResponseBody",
            "type": "object",
        },
        {
            "properties": {
                "capacity": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
                "id": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
                "name": {"oneOf": [{"type": "null"}, {"type": "string"}]},
            },
            "required": [],
            "title": "tests.app.endpoints.retrieve_venuesVenueResponseBody",
            "type": "object",
        },
    )
