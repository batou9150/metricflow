from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Optional

from dbt_semantic_interfaces.protocols import WhereFilter
from typing_extensions import override

from metricflow.formatting import indent_log_line
from metricflow.query.group_by_item.resolution_nodes.base_node import GroupByItemResolutionNode
from metricflow.query.issues.issues_base import (
    MetricFlowQueryIssueType,
    MetricFlowQueryResolutionIssue,
    MetricFlowQueryResolutionPath,
)
from metricflow.query.resolver_inputs.query_resolver_inputs import MetricFlowQueryResolverInput


@dataclass(frozen=True)
class WhereFilterParsingIssue(MetricFlowQueryResolutionIssue):
    """TODO: Add test for this issue."""

    where_filter: WhereFilter
    parse_exception: Exception

    @staticmethod
    def from_parameters(
        where_filter: WhereFilter,
        parse_exception: Exception,
        query_resolution_path: MetricFlowQueryResolutionPath,
    ) -> WhereFilterParsingIssue:
        return WhereFilterParsingIssue(
            issue_type=MetricFlowQueryIssueType.ERROR,
            parent_issues=(),
            query_resolution_path=query_resolution_path,
            where_filter=where_filter,
            parse_exception=parse_exception,
        )

    @override
    def ui_description(self, associated_input: Optional[MetricFlowQueryResolverInput]) -> str:
        return (
            f"Error parsing where filter:\n\n"
            f"{indent_log_line(repr(self.where_filter.where_sql_template))}\n\n"
            f"Got exception:\n\n"
            f"{indent_log_line(''.join(traceback.TracebackException.from_exception(self.parse_exception).format()))}"
        )

    @override
    def with_path_prefix(self, path_prefix_node: GroupByItemResolutionNode) -> WhereFilterParsingIssue:
        return WhereFilterParsingIssue(
            issue_type=self.issue_type,
            parent_issues=tuple(issue.with_path_prefix(path_prefix_node) for issue in self.parent_issues),
            query_resolution_path=self.query_resolution_path.with_path_prefix(path_prefix_node),
            where_filter=self.where_filter,
            parse_exception=self.parse_exception,
        )
