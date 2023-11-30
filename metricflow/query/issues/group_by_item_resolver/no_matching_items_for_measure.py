from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from typing_extensions import override

from metricflow.query.group_by_item.resolution_dag.resolution_nodes.base_node import GroupByItemResolutionNode
from metricflow.query.group_by_item.resolution_path import MetricFlowQueryResolutionPath
from metricflow.query.issues.issues_base import (
    MetricFlowQueryIssueType,
    MetricFlowQueryResolutionIssue,
)
from metricflow.query.resolver_inputs.base_resolver_inputs import MetricFlowQueryResolverInput


@dataclass(frozen=True)
class NoMatchingItemsForMeasure(MetricFlowQueryResolutionIssue):
    """Describes an issue with the query where there are no matching items for a measure.

    This can happen if the user specifies a group-by-item that does not exist or is not available for the measure.
    """

    @staticmethod
    def from_parameters(  # noqa: D
        parent_issues: Sequence[MetricFlowQueryResolutionIssue],
        query_resolution_path: MetricFlowQueryResolutionPath,
    ) -> NoMatchingItemsForMeasure:
        return NoMatchingItemsForMeasure(
            issue_type=MetricFlowQueryIssueType.ERROR,
            parent_issues=tuple(parent_issues),
            query_resolution_path=query_resolution_path,
        )

    @override
    def ui_description(self, associated_input: MetricFlowQueryResolverInput) -> str:
        # Could be useful to list the candidates, but it makes the logs very long.
        return (
            f"The given input does not match any of the available group by items for "
            f"{self.query_resolution_path.last_item.ui_description}."
        )

    @override
    def with_path_prefix(self, path_prefix_node: GroupByItemResolutionNode) -> NoMatchingItemsForMeasure:
        return NoMatchingItemsForMeasure(
            issue_type=self.issue_type,
            parent_issues=tuple(issue.with_path_prefix(path_prefix_node) for issue in self.parent_issues),
            query_resolution_path=self.query_resolution_path.with_path_prefix(path_prefix_node),
        )