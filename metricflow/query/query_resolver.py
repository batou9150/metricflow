from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from dbt_semantic_interfaces.references import MetricReference

from metricflow.collection_helpers.pretty_print import mf_pformat
from metricflow.dag.dag_to_text import dag_as_text
from metricflow.model.semantic_manifest_lookup import SemanticManifestLookup
from metricflow.query.group_by_item.filter_spec_resolution.filter_spec_lookup import FilterSpecResolutionLookUp
from metricflow.query.group_by_item.filter_spec_resolution.filter_spec_resolver import (
    WhereFilterSpecResolver,
)
from metricflow.query.group_by_item.group_by_item_resolver import GroupByItemResolution, GroupByItemResolver
from metricflow.query.group_by_item.resolution_dag.dag import GroupByItemResolutionDag
from metricflow.query.group_by_item.resolution_dag.dag_builder import GroupByItemResolutionDagBuilder
from metricflow.query.group_by_item.resolution_dag.resolution_nodes.query_resolution_node import (
    QueryGroupByItemResolutionNode,
)
from metricflow.query.group_by_item.resolution_path import MetricFlowQueryResolutionPath
from metricflow.query.issues.issues_base import (
    MetricFlowQueryResolutionIssueSet,
)
from metricflow.query.issues.parsing.invalid_limit import InvalidLimitIssue
from metricflow.query.issues.parsing.invalid_metric import InvalidMetricIssue
from metricflow.query.issues.parsing.invalid_order import InvalidOrderByItemIssue
from metricflow.query.query_resolution import (
    InputToIssueSetMapping,
    InputToIssueSetMappingItem,
    MetricFlowQueryResolution,
)
from metricflow.query.resolver_inputs.query_resolver_inputs import (
    ResolverInputForGroupByItem,
    ResolverInputForLimit,
    ResolverInputForMetric,
    ResolverInputForOrderByItem,
    ResolverInputForQuery,
    ResolverInputForWhereFilterIntersection,
)
from metricflow.query.validation_rules.query_validator import PostResolutionQueryValidator
from metricflow.specs.specs import (
    InstanceSpec,
    LinkableInstanceSpec,
    LinkableSpecSet,
    MetricFlowQuerySpec,
    MetricSpec,
    OrderBySpec,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolveOrderByResult:
    """Result of resolving order-by inputs to specs."""

    order_by_specs: Tuple[OrderBySpec, ...]
    input_to_issue_set_mapping: InputToIssueSetMapping


@dataclass(frozen=True)
class ResolveMetricsResult:
    """Result of resolving a metric input to specs."""

    metric_specs: Tuple[MetricSpec, ...]
    input_to_issue_set_mapping: InputToIssueSetMapping


@dataclass(frozen=True)
class ResolveLimitResult:
    """Result of resolving a limit input."""

    limit: Optional[int]
    input_to_issue_set_mapping: InputToIssueSetMapping


@dataclass(frozen=True)
class ResolveGroupByItemsResult:
    """Result of resolving group-by inputs to specs."""

    resolution_dag: GroupByItemResolutionDag
    group_by_item_specs: Tuple[LinkableInstanceSpec, ...]
    input_to_issue_set_mapping: InputToIssueSetMapping


class MetricFlowQueryResolver:
    """Resolves different parts of a query into concrete specs, and returns an issue set if there are problems."""

    def __init__(self, manifest_lookup: SemanticManifestLookup) -> None:  # noqa: D
        self._manifest_lookup = manifest_lookup
        self._post_resolution_query_validator = PostResolutionQueryValidator(
            manifest_lookup=self._manifest_lookup,
        )

    def _resolve_group_by_item_input(
        self, resolution_dag: GroupByItemResolutionDag, group_by_item_input: ResolverInputForGroupByItem
    ) -> GroupByItemResolution:
        group_by_item_resolver = GroupByItemResolver(
            manifest_lookup=self._manifest_lookup,
            resolution_dag=resolution_dag,
        )

        return group_by_item_resolver.resolve_matching_item_for_querying(
            spec_pattern=group_by_item_input.spec_pattern,
        )

    def _resolve_metric_inputs(
        self,
        metric_inputs: Sequence[ResolverInputForMetric],
        query_resolution_path: MetricFlowQueryResolutionPath,
    ) -> ResolveMetricsResult:
        all_metric_specs = tuple(
            MetricSpec.from_reference(metric_reference)
            for metric_reference in self._manifest_lookup.metric_lookup.metric_references
        )
        metric_specs: List[MetricSpec] = []
        input_to_issue_set_mapping_items: List[InputToIssueSetMappingItem] = []

        for metric_input in metric_inputs:
            matching_specs = metric_input.spec_pattern.match(all_metric_specs)
            if len(matching_specs) != 1:
                input_to_issue_set_mapping_items.append(
                    InputToIssueSetMappingItem(
                        resolver_input=metric_input,
                        issue_set=MetricFlowQueryResolutionIssueSet.from_issue(
                            InvalidMetricIssue.from_parameters(
                                candidate_metric_references=self._manifest_lookup.metric_lookup.metric_references,
                                query_resolution_path=query_resolution_path,
                            )
                        ),
                    )
                )
            else:
                metric_specs.extend(matching_specs)

        return ResolveMetricsResult(
            metric_specs=tuple(metric_specs),
            input_to_issue_set_mapping=InputToIssueSetMapping(items=tuple(input_to_issue_set_mapping_items)),
        )

    def _resolve_group_by_items_result(
        self,
        metric_references: Sequence[MetricReference],
        group_by_item_inputs: Sequence[ResolverInputForGroupByItem],
        filter_input: ResolverInputForWhereFilterIntersection,
    ) -> ResolveGroupByItemsResult:
        resolution_dag_builder = GroupByItemResolutionDagBuilder(
            manifest_lookup=self._manifest_lookup,
        )
        resolution_dag = resolution_dag_builder.build(
            metric_references=metric_references,
            where_filter_intersection=filter_input.where_filter_intersection,
        )
        logger.info(f"Resolution DAG is:\n{dag_as_text(resolution_dag)}")

        input_to_issue_set_mapping_items: List[InputToIssueSetMappingItem] = []
        group_by_item_specs: List[LinkableInstanceSpec] = []
        for group_by_item_input in group_by_item_inputs:
            resolution = self._resolve_group_by_item_input(
                resolution_dag=resolution_dag, group_by_item_input=group_by_item_input
            )
            if resolution.issue_set.has_issues:
                input_to_issue_set_mapping_items.append(
                    InputToIssueSetMappingItem(resolver_input=group_by_item_input, issue_set=resolution.issue_set)
                )
            if resolution.spec is not None:
                group_by_item_specs.append(resolution.spec)

        return ResolveGroupByItemsResult(
            resolution_dag=resolution_dag,
            group_by_item_specs=tuple(group_by_item_specs),
            input_to_issue_set_mapping=InputToIssueSetMapping(tuple(input_to_issue_set_mapping_items)),
        )

    def _resolve_order_by(
        self,
        resolver_inputs_for_order_by_items: Sequence[ResolverInputForOrderByItem],
        metric_specs: Sequence[MetricSpec],
        group_by_item_specs: Sequence[LinkableInstanceSpec],
        query_resolution_path: MetricFlowQueryResolutionPath,
    ) -> ResolveOrderByResult:
        mapping_items: List[InputToIssueSetMappingItem] = []
        order_by_specs: List[OrderBySpec] = []
        for resolver_input_for_order_by in resolver_inputs_for_order_by_items:
            matching_specs: List[InstanceSpec] = []
            for possible_input in resolver_input_for_order_by.possible_inputs:
                spec_pattern = possible_input.spec_pattern
                matching_specs.extend(spec_pattern.match(metric_specs))
                matching_specs.extend(spec_pattern.match(group_by_item_specs))

            if len(matching_specs) != 1:
                mapping_items.append(
                    InputToIssueSetMappingItem(
                        resolver_input=resolver_input_for_order_by,
                        issue_set=MetricFlowQueryResolutionIssueSet.from_issue(
                            InvalidOrderByItemIssue.from_parameters(
                                order_by_item_input=resolver_input_for_order_by,
                                query_resolution_path=query_resolution_path,
                            )
                        ),
                    )
                )
            else:
                order_by_specs.append(
                    OrderBySpec(
                        instance_spec=matching_specs[0],
                        descending=resolver_input_for_order_by.descending,
                    )
                )

        return ResolveOrderByResult(
            input_to_issue_set_mapping=InputToIssueSetMapping(items=tuple(mapping_items)),
            order_by_specs=tuple(order_by_specs),
        )

    @staticmethod
    def _resolve_limit_input(
        limit_input: ResolverInputForLimit, query_resolution_path: MetricFlowQueryResolutionPath
    ) -> ResolveLimitResult:
        limit = limit_input.limit
        if limit is not None and limit < 0:
            return ResolveLimitResult(
                limit=limit,
                input_to_issue_set_mapping=InputToIssueSetMapping.from_one_item(
                    resolver_input=limit_input,
                    issue_set=MetricFlowQueryResolutionIssueSet.from_issue(
                        InvalidLimitIssue.from_parameters(limit=limit, query_resolution_path=query_resolution_path),
                    ),
                ),
            )
        return ResolveLimitResult(limit=limit, input_to_issue_set_mapping=InputToIssueSetMapping.empty_instance())

    def _resolve_where(
        self,
        resolution_dag: GroupByItemResolutionDag,
    ) -> FilterSpecResolutionLookUp:
        where_filter_spec_resolver = WhereFilterSpecResolver(
            manifest_lookup=self._manifest_lookup,
            resolution_dag=resolution_dag,
        )

        return where_filter_spec_resolver.resolve_lookup()

    def resolve_query(self, resolver_input_for_query: ResolverInputForQuery) -> MetricFlowQueryResolution:
        """Resolve the query into specs that can be passed into the next stage in query processing."""
        metric_inputs = resolver_input_for_query.metric_inputs
        group_by_item_inputs = resolver_input_for_query.group_by_item_inputs
        order_by_item_inputs = resolver_input_for_query.order_by_item_inputs
        limit_input = resolver_input_for_query.limit_input
        filter_input = resolver_input_for_query.filter_input

        # Define a resolution path for issues where the input is considered to be the whole query.
        query_resolution_path = MetricFlowQueryResolutionPath.from_path_item(
            QueryGroupByItemResolutionNode(
                parent_nodes=(),
                metrics_in_query=tuple(metric_input.spec_pattern.metric_reference for metric_input in metric_inputs),
                where_filter_intersection=filter_input.where_filter_intersection,
            )
        )

        mappings_to_merge: List[InputToIssueSetMapping] = []

        # Resolve metrics.
        resolve_metrics_result = self._resolve_metric_inputs(metric_inputs, query_resolution_path=query_resolution_path)
        mappings_to_merge.append(resolve_metrics_result.input_to_issue_set_mapping)
        metric_specs = resolve_metrics_result.metric_specs

        # Resolve limit
        resolve_limit_result = self._resolve_limit_input(
            limit_input=limit_input,
            query_resolution_path=query_resolution_path,
        )
        mappings_to_merge.append(resolve_limit_result.input_to_issue_set_mapping)

        # Early stop before resolving further as with invalid metrics, the errors won't be as useful.
        issue_set_mapping_so_far = InputToIssueSetMapping.merge_iterable(mappings_to_merge)
        if issue_set_mapping_so_far.has_issues:
            return MetricFlowQueryResolution(
                query_spec=None,
                resolution_dag=None,
                filter_spec_lookup=FilterSpecResolutionLookUp.empty_instance(),
                input_to_issue_set=issue_set_mapping_so_far,
            )

        # Resolve group by items.
        resolve_group_by_item_result = self._resolve_group_by_items_result(
            metric_references=tuple(metric_spec.reference for metric_spec in metric_specs),
            group_by_item_inputs=group_by_item_inputs,
            filter_input=filter_input,
        )
        resolution_dag = resolve_group_by_item_result.resolution_dag
        group_by_item_specs = resolve_group_by_item_result.group_by_item_specs
        mappings_to_merge.append(resolve_group_by_item_result.input_to_issue_set_mapping)

        # Resolve order by.
        resolve_order_by_result = self._resolve_order_by(
            resolver_inputs_for_order_by_items=order_by_item_inputs,
            metric_specs=metric_specs,
            group_by_item_specs=group_by_item_specs,
            query_resolution_path=query_resolution_path,
        )
        order_by_specs = resolve_order_by_result.order_by_specs
        if resolve_order_by_result.input_to_issue_set_mapping.has_issues:
            mappings_to_merge.append(resolve_order_by_result.input_to_issue_set_mapping)

        # Resolve where.
        filter_spec_lookup = self._resolve_where(
            resolution_dag=resolution_dag,
        )

        if filter_spec_lookup.issue_set.has_issues:
            mappings_to_merge.append(
                InputToIssueSetMapping.from_one_item(
                    resolver_input=filter_input,
                    issue_set=filter_spec_lookup.issue_set,
                )
            )

        # Return if there are any errors since additional fields would not be useful.
        issue_set_mapping_so_far = InputToIssueSetMapping.merge_iterable(mappings_to_merge)
        if issue_set_mapping_so_far.has_issues:
            return MetricFlowQueryResolution(
                query_spec=None,
                resolution_dag=resolution_dag,
                filter_spec_lookup=filter_spec_lookup,
                input_to_issue_set=issue_set_mapping_so_far,
            )

        # No errors.
        linkable_spec_set = LinkableSpecSet.from_specs(group_by_item_specs)
        logger.info(f"Group-by-items were resolved to:\n{mf_pformat(linkable_spec_set.as_tuple)}")

        # Run post-resolution validation rules to generate issues that are generated at the query-level.
        query_level_issue_set = self._post_resolution_query_validator.validate_query(
            resolution_dag=resolution_dag,
            resolver_input_for_query=resolver_input_for_query,
        )

        if query_level_issue_set.has_issues:
            mappings_to_merge.append(
                InputToIssueSetMapping(
                    (
                        InputToIssueSetMappingItem(
                            resolver_input=resolver_input_for_query,
                            issue_set=query_level_issue_set,
                        ),
                    )
                )
            )

        issue_set_mapping = InputToIssueSetMapping.merge_iterable(mappings_to_merge)

        if issue_set_mapping.has_issues:
            return MetricFlowQueryResolution(
                query_spec=None,
                resolution_dag=resolution_dag,
                filter_spec_lookup=filter_spec_lookup,
                input_to_issue_set=issue_set_mapping,
            )

        return MetricFlowQueryResolution(
            query_spec=MetricFlowQuerySpec(
                metric_specs=metric_specs,
                dimension_specs=linkable_spec_set.dimension_specs,
                entity_specs=linkable_spec_set.entity_specs,
                time_dimension_specs=linkable_spec_set.time_dimension_specs,
                order_by_specs=tuple(order_by_specs),
                limit=limit_input.limit,
                filter_intersection=filter_input.where_filter_intersection,
                filter_spec_resolution_lookup=filter_spec_lookup,
            ),
            resolution_dag=resolution_dag,
            filter_spec_lookup=filter_spec_lookup,
            input_to_issue_set=issue_set_mapping,
        )
