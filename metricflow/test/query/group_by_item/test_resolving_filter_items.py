from __future__ import annotations

import logging
from typing import Dict

import pytest
from _pytest.fixtures import FixtureRequest
from dbt_semantic_interfaces.naming.keywords import METRIC_TIME_ELEMENT_NAME

from metricflow.collection_helpers.pretty_print import mf_pformat
from metricflow.model.semantic_manifest_lookup import SemanticManifestLookup
from metricflow.naming.naming_scheme import QueryItemNamingScheme
from metricflow.naming.object_builder_scheme import ObjectBuilderNamingScheme
from metricflow.query.group_by_item.group_by_item_resolver import GroupByItemResolver
from metricflow.query.group_by_item.resolution_dag import GroupByItemResolutionDag
from metricflow.test.fixtures.setup_fixtures import MetricFlowTestSessionState
from metricflow.test.query.group_by_item.conftest import AmbiguousResolutionQueryId
from metricflow.test.snapshot_utils import assert_object_snapshot_equal

logger = logging.getLogger(__name__)


@pytest.mark.parametrize("dag_case_id", [case_id.value for case_id in AmbiguousResolutionQueryId])
def test_ambiguous_metric_time_in_query_filter(  # noqa: D
    request: FixtureRequest,
    mf_test_session_state: MetricFlowTestSessionState,
    naming_scheme: QueryItemNamingScheme,
    ambiguous_resolution_manifest_lookup: SemanticManifestLookup,
    resolution_dags: Dict[AmbiguousResolutionQueryId, GroupByItemResolutionDag],
    dag_case_id: str,
) -> None:
    case_id = AmbiguousResolutionQueryId(dag_case_id)
    resolution_dag = resolution_dags[case_id]
    group_by_item_resolver = GroupByItemResolver(
        manifest_lookup=ambiguous_resolution_manifest_lookup,
        resolution_dag=resolution_dag,
    )

    spec_pattern = ObjectBuilderNamingScheme().spec_pattern(f"TimeDimension('{METRIC_TIME_ELEMENT_NAME}')")

    result = group_by_item_resolver.resolve_matching_item_for_where_filter(
        spec_pattern=spec_pattern,
        resolution_node=resolution_dag.sink_node,
    )

    assert_object_snapshot_equal(
        request=request,
        mf_test_session_state=mf_test_session_state,
        obj_id="result",
        obj=mf_pformat(result),
    )
