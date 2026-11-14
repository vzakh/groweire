"""Field request/response schemas (brief §9.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PolygonIn(BaseModel):
    """GeoJSON Polygon in EPSG:4326. Checked in depth by services/fields.py."""

    type: str = Field(examples=["Polygon"])
    coordinates: list[list[list[float]]] = Field(max_length=20)


class FieldCreate(BaseModel):
    """EXACTLY ONE of {point + area_ha} (default, PRD DD-2) or {geometry}."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"name": "Home field", "point": [-6.955, 52.705], "area_ha": 10},
                {
                    "name": "Home field",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-7.25, 52.65],
                                [-7.24, 52.65],
                                [-7.24, 52.66],
                                [-7.25, 52.66],
                                [-7.25, 52.65],
                            ]
                        ],
                    },
                },
            ]
        },
    )

    name: str | None = Field(default=None, max_length=80)
    point: tuple[float, float] | None = Field(default=None, description="[lon, lat]")
    area_ha: float | None = Field(default=None, description="Approximate size, 0.1 to 2,000 ha")
    geometry: PolygonIn | None = None

    @model_validator(mode="after")
    def exactly_one_shape(self) -> "FieldCreate":
        has_point = self.point is not None or self.area_ha is not None
        has_geometry = self.geometry is not None
        if has_point == has_geometry:
            raise ValueError(
                "code=field_input_ambiguous: Send either point + area_ha, or geometry. Not both."
            )
        if has_point and (self.point is None or self.area_ha is None):
            raise ValueError("code=field_input_ambiguous: point and area_ha must come together.")
        return self


class FieldOut(BaseModel):
    field_id: str = Field(examples=["f_8c1e02ab"])
    name: str | None = None
    area_ha: float
    area_source: Literal["approximate", "drawn"]
    centroid: tuple[float, float] = Field(description="[lon, lat]")
    pilot_coverage: bool = Field(description="True when the risk model is calibrated here (IE)")
    cell_ids: list[str]
    geometry: dict = Field(
        description="GeoJSON Polygon of the stored field (a circle if approximate)"
    )
