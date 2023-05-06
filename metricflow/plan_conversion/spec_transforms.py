from __future__ import annotations

from typing import Sequence, List

from metricflow.column_assoc import ColumnAssociation
from metricflow.plan_conversion.select_column_gen import SelectColumnSet
from metricflow.plan_conversion.sql_expression_builders import make_coalesced_expr
from metricflow.specs import (
    InstanceSpecSetTransform,
    InstanceSpecSet,
    ColumnAssociationResolver,
)
from metricflow.sql.sql_plan import SqlSelectColumn


class CreateSelectCoalescedColumnsForLinkableSpecs(InstanceSpecSetTransform[SelectColumnSet]):
    """Create select columns that coalesce columns corresponding to linkable specs.

    e.g.

    dimension_specs = [DimensionSpec(element_name="is_instant")]
    table_aliases = ["a", "b"]

    ->

    COALESCE(a.is_instant, b.is_instant) AS is_instant
    """

    def __init__(  # noqa: D
        self,
        column_association_resolver: ColumnAssociationResolver,
        table_aliases: Sequence[str],
    ) -> None:
        self._column_association_resolver = column_association_resolver
        self._table_aliases = table_aliases

    def transform(self, spec_set: InstanceSpecSet) -> SelectColumnSet:  # noqa: D

        dimension_columns: List[SqlSelectColumn] = []
        time_dimension_columns: List[SqlSelectColumn] = []
        entity_columns: List[SqlSelectColumn] = []

        for dimension_spec in spec_set.dimension_specs:
            column_name = self._column_association_resolver.resolve_dimension_spec(dimension_spec).column_name
            dimension_columns.append(
                SqlSelectColumn(
                    expr=make_coalesced_expr(self._table_aliases, column_name),
                    column_alias=column_name,
                )
            )

        for time_dimension_spec in spec_set.time_dimension_specs:
            column_name = self._column_association_resolver.resolve_time_dimension_spec(time_dimension_spec).column_name
            time_dimension_columns.append(
                SqlSelectColumn(
                    expr=make_coalesced_expr(self._table_aliases, column_name),
                    column_alias=column_name,
                )
            )

        for entity_spec in spec_set.entity_specs:
            column_name = self._column_association_resolver.resolve_entity_spec(entity_spec).column_name

            entity_columns.append(
                SqlSelectColumn(
                    expr=make_coalesced_expr(self._table_aliases, column_name),
                    column_alias=column_name,
                )
            )

        return SelectColumnSet(
            dimension_columns=dimension_columns,
            time_dimension_columns=time_dimension_columns,
            entity_columns=entity_columns,
        )


class SelectOnlyLinkableSpecs(InstanceSpecSetTransform[InstanceSpecSet]):
    """Removes metrics and measures from the spec set."""

    def transform(self, spec_set: InstanceSpecSet) -> InstanceSpecSet:  # noqa: D
        return InstanceSpecSet(
            metric_specs=(),
            measure_specs=(),
            dimension_specs=spec_set.dimension_specs,
            time_dimension_specs=spec_set.time_dimension_specs,
            entity_specs=spec_set.entity_specs,
        )


class CreateColumnAssociations(InstanceSpecSetTransform[Sequence[ColumnAssociation]]):
    """Using the specs in the instance set, generate the associated column associations.

    Initial use case is to figure out names of the columns present in the SQL of a WhereFilter.
    """

    def __init__(self, column_association_resolver: ColumnAssociationResolver) -> None:  # noqa: D
        self._column_association_resolver = column_association_resolver

    def transform(self, spec_set: InstanceSpecSet) -> Sequence[ColumnAssociation]:  # noqa: D
        column_associations: List[ColumnAssociation] = []
        for measure_spec in spec_set.measure_specs:
            column_associations.append(self._column_association_resolver.resolve_measure_spec(measure_spec))
        for dimension_spec in spec_set.dimension_specs:
            column_associations.append(self._column_association_resolver.resolve_dimension_spec(dimension_spec))
        for time_dimension_spec in spec_set.time_dimension_specs:
            column_associations.append(
                self._column_association_resolver.resolve_time_dimension_spec(time_dimension_spec)
            )
        for entity_spec in spec_set.entity_specs:
            column_associations.extend(self._column_association_resolver.resolve_entity_spec(entity_spec))
        for metric_spec in spec_set.metric_specs:
            column_associations.append(self._column_association_resolver.resolve_metric_spec(metric_spec))
        for metadata_spec in spec_set.metadata_specs:
            column_associations.append(self._column_association_resolver.resolve_metadata_spec(metadata_spec))
        return column_associations
