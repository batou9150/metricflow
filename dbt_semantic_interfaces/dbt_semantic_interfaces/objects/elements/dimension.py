from __future__ import annotations

from typing import Optional

from dbt_semantic_interfaces.objects.base import HashableBaseModel, ModelWithMetadataParsing
from dbt_semantic_interfaces.objects.common import Metadata
from dbt_semantic_interfaces.references import DimensionReference, TimeDimensionReference
from dbt_semantic_interfaces.enum_extension import ExtendedEnum
from dbt_semantic_interfaces.objects.time_granularity import TimeGranularity

ISO8601_FMT = "YYYY-MM-DD"


class DimensionType(ExtendedEnum):
    """Determines types of values expected of dimensions."""

    CATEGORICAL = "categorical"
    TIME = "time"

    def is_time_type(self) -> bool:
        """Checks if this type of dimension is a time type"""
        return self in [DimensionType.TIME]


class DimensionValidityParams(HashableBaseModel):
    """Parameters identifying a given dimension as an entity for validity state

    This construct is used for supporting SCD Type II tables, such as might be
    created via dbt's snapshot feature, or generated via periodic loads from external
    dimension data sources. In either of those cases, there is typically a time dimension
    associated with the SCD data source that indicates the start and end times of a
    validity window, where the dimension value is valid for any time within that range.
    """

    is_start: bool = False
    is_end: bool = False


class DimensionTypeParams(HashableBaseModel):
    """Dimension type params add additional context to some types (time) of dimensions"""

    is_primary: bool = False
    time_granularity: TimeGranularity
    validity_params: Optional[DimensionValidityParams] = None


class Dimension(HashableBaseModel, ModelWithMetadataParsing):
    """Describes a dimension"""

    name: str
    description: Optional[str]
    type: DimensionType
    is_partition: bool = False
    type_params: Optional[DimensionTypeParams]
    expr: Optional[str] = None
    metadata: Optional[Metadata]

    @property
    def is_primary_time(self) -> bool:  # noqa: D
        if self.type == DimensionType.TIME and self.type_params is not None:
            return self.type_params.is_primary

        return False

    @property
    def reference(self) -> DimensionReference:  # noqa: D
        return DimensionReference(element_name=self.name)

    @property
    def time_dimension_reference(self) -> TimeDimensionReference:  # noqa: D
        assert self.type == DimensionType.TIME, f"Got type as {self.type} instead of {DimensionType.TIME}"
        return TimeDimensionReference(element_name=self.name)

    @property
    def validity_params(self) -> Optional[DimensionValidityParams]:
        """Returns the DimensionValidityParams property, if it exists.

        This is to avoid repeatedly checking that type params is not None before doing anything with ValidityParams
        """
        if self.type_params:
            return self.type_params.validity_params

        return None
