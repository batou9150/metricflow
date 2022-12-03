from typing import Tuple

from dbt_metadata_client.dbt_metadata_api_schema import MetricNode
from metricflow.model.dbt_converter import DbtConverter
from metricflow.model.dbt_mapping_rules.dbt_metric_to_dimensions_rules import (
    DbtDimensionsToDimensions,
    DbtTimestampToDimension,
    DbtFiltersToDimensions,
)
from metricflow.model.dbt_mapping_rules.dbt_metric_to_metrics_rules import CALC_METHOD_TO_METRIC_TYPE
from metricflow.model.dbt_mapping_rules.dbt_mapping_rule import MappedObjects, DbtMappingRule
from metricflow.model.objects.elements.dimension import DimensionType
from metricflow.model.objects.metric import MetricType


def test_dbt_metric_to_dimensions_rules_skip_derived_metrics(dbt_metrics: Tuple[MetricNode, ...]) -> None:  # noqa: D
    derived_metrics = tuple(dbt_metric for dbt_metric in dbt_metrics if dbt_metric.calculation_method == "derived")
    rules: Tuple[DbtMappingRule, ...] = (
        DbtDimensionsToDimensions(),
        DbtTimestampToDimension(),
        DbtFiltersToDimensions(),
    )
    converter = DbtConverter(rules=rules)
    result = converter._map_dbt_to_metricflow(dbt_metrics=derived_metrics)
    assert (
        len(result.mapped_objects.dimensions.keys()) == 0
    ), "Derived dbt metrics created dimensions, and they shouldn't"


def test_dbt_dimensions_to_dimensions(dbt_metrics: Tuple[MetricNode, ...]) -> None:  # noqa: D
    objects = MappedObjects()
    issues = DbtDimensionsToDimensions().run(dbt_metrics=dbt_metrics, objects=objects)
    assert (
        not issues.has_blocking_issues
    ), f"DbtDimensionsToDimensions raised blocking issues when it shouldn't have: {issues.to_pretty_json()}"
    for dbt_metric in dbt_metrics:
        if CALC_METHOD_TO_METRIC_TYPE[dbt_metric.calculation_method] != MetricType.DERIVED:
            for dimension in dbt_metric.dimensions:
                assert (
                    objects.dimensions[dbt_metric.model.name].get(dimension) is not None
                ), f"Failed to build dimension `{dimension}` for data source `{dbt_metric.model.name}` of dbt metric `{dbt_metric.name}`"


def test_dbt_dimensions_to_dimensions_no_issues_when_no_dimensions(  # noqa: D
    dbt_metrics: Tuple[MetricNode, ...]
) -> None:
    objects = MappedObjects()
    dbt_metrics[0].dimensions = None
    issues = DbtDimensionsToDimensions().run(dbt_metrics=dbt_metrics, objects=objects)
    assert (
        not issues.has_blocking_issues
    ), f"DbtDimensionsToDimensions raised blocking issues when it shouldn't have: {issues.to_pretty_json()}"


def test_dbt_timestamp_to_dimension(dbt_metrics: Tuple[MetricNode, ...]) -> None:  # noqa: D
    objects = MappedObjects()
    issues = DbtTimestampToDimension().run(dbt_metrics=dbt_metrics, objects=objects)
    assert (
        not issues.has_blocking_issues
    ), f"DbtTimestampToDimension raised blocking issues when it shouldn't have: {issues.to_pretty_json()}"
    for dbt_metric in dbt_metrics:
        if CALC_METHOD_TO_METRIC_TYPE[dbt_metric.calculation_method] != MetricType.DERIVED:
            # each dbt metric timestamp creates 1 dimension, and a dbt metric must have exactly one timestamp
            assert (
                len(objects.dimensions[dbt_metric.model.name].keys()) == 1
            ), f"A dbt metric timestamp should only create 1 dimension, but {len(objects.dimensions[dbt_metric.model.name].keys())} were created"
            assert (
                objects.dimensions[dbt_metric.model.name][dbt_metric.timestamp]["type"] == DimensionType.TIME
            ), f"A TIME type dimension should be created from a dbt metric timestamp, but a `{objects.dimensions[dbt_metric.model.name][dbt_metric.timestamp]['type']}` was created"


def test_dbt_timestamp_to_dimension_missing_timestamp_issue(dbt_metrics: Tuple[MetricNode, ...]) -> None:  # noqa: D
    objects = MappedObjects()
    dbt_metrics[0].timestamp = None
    issues = DbtTimestampToDimension().run(dbt_metrics=dbt_metrics, objects=objects)
    assert (
        issues.has_blocking_issues
    ), f"DbtTimestampToDimension didn't raise blocking issues when it should have: {issues.to_pretty_json()}"


def test_dbt_filters_to_dimensions(dbt_metrics: Tuple[MetricNode, ...]) -> None:  # noqa: D
    objects = MappedObjects()
    issues = DbtFiltersToDimensions().run(dbt_metrics=dbt_metrics, objects=objects)
    assert (
        not issues.has_blocking_issues
    ), f"DbtFiltersToDimension raised blocking issues when it shouldn't have: {issues.to_pretty_json()}"
    for dbt_metric in dbt_metrics:
        if CALC_METHOD_TO_METRIC_TYPE[dbt_metric.calculation_method] != MetricType.DERIVED and dbt_metric.filters:
            # as many dimensions should be created as their are filters
            assert len(objects.dimensions[dbt_metric.model.name].keys()) == len(
                dbt_metric.filters
            ), f"DbtFiltersToDimensions should have created as many dimensions as filters. We expected {len(dbt_metric.filters)}, but {len(objects.dimensions[dbt_metric.model.name].keys())} were created"


def test_dbt_filters_to_dimensions_no_filters_okay(dbt_metrics: Tuple[MetricNode, ...]) -> None:  # noqa: D
    objects = MappedObjects()
    dbt_metrics[0].filters = None
    issues = DbtFiltersToDimensions().run(dbt_metrics=dbt_metrics, objects=objects)
    assert (
        not issues.has_blocking_issues
    ), f"DbtFiltersToDimension raised blocking issues when it shouldn't have: {issues.to_pretty_json()}"
    assert (
        objects.dimensions.get(dbt_metrics[0].model.name) is None
    ), f"No filters should have been created, but {len(objects.dimensions[dbt_metrics[0].model.name].keys())} were created"