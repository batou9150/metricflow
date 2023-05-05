from __future__ import annotations

import logging
import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Dict, Sequence

import pytest

from metricflow.dataflow.builder.source_node import SourceNodeBuilder
from metricflow.dataflow.dataflow_plan import ReadSqlSourceNode, BaseOutput
from metricflow.dataset.convert_data_source import DataSourceToDataSetConverter
from dbt_semantic_interfaces.model_transformer import ModelTransformer
from metricflow.model.model_validator import ModelValidator
from dbt_semantic_interfaces.objects.data_source import DataSource
from dbt_semantic_interfaces.objects.user_configured_model import UserConfiguredModel
from dbt_semantic_interfaces.parsing.dir_to_model import (
    parse_directory_of_yaml_files_to_model,
    parse_yaml_files_to_validation_ready_model,
)
from metricflow.model.semantic_model import SemanticModel
from metricflow.plan_conversion.column_resolver import DefaultColumnAssociationResolver
from metricflow.dataset.data_source_adapter import DataSourceDataSet
from metricflow.test.fixtures.id_fixtures import IdNumberSpace, patch_id_generators_helper
from metricflow.test.fixtures.setup_fixtures import MetricFlowTestSessionState
from metricflow.dataflow.builder.node_data_set import DataflowPlanNodeOutputDataSetResolver
from dbt_semantic_interfaces.parsing.objects import YamlConfigFile
from metricflow.plan_conversion.time_spine import TimeSpineSource
from metricflow.query.query_parser import MetricFlowQueryParser

logger = logging.getLogger(__name__)


def _data_set_to_read_nodes(
    data_sets: OrderedDict[str, DataSourceDataSet]
) -> OrderedDict[str, ReadSqlSourceNode[DataSourceDataSet]]:
    """Return a mapping from the name of the data source to the dataflow plan node that reads from it."""
    return_dict: OrderedDict[str, ReadSqlSourceNode[DataSourceDataSet]] = OrderedDict()
    for data_source_name, data_set in data_sets.items():
        return_dict[data_source_name] = ReadSqlSourceNode[DataSourceDataSet](data_set)
        logger.debug(f"For data source {data_source_name}, creating node_id {return_dict[data_source_name].node_id}")

    return return_dict


def _data_set_to_source_nodes(
    semantic_model: SemanticModel, data_sets: OrderedDict[str, DataSourceDataSet]
) -> Sequence[BaseOutput[DataSourceDataSet]]:
    source_node_builder = SourceNodeBuilder(semantic_model)
    return source_node_builder.create_from_data_sets(list(data_sets.values()))


def query_parser_from_yaml(
    yaml_contents: List[YamlConfigFile], time_spine_source: TimeSpineSource
) -> MetricFlowQueryParser:
    """Given yaml files, return a query parser using default source nodes, resolvers and time spine source"""
    semantic_model = SemanticModel(parse_yaml_files_to_validation_ready_model(yaml_contents).model)
    ModelValidator().checked_validations(semantic_model.user_configured_model)
    source_nodes = _data_set_to_source_nodes(semantic_model, create_data_sets(semantic_model))
    return MetricFlowQueryParser(
        column_association_resolver=DefaultColumnAssociationResolver(semantic_model),
        model=semantic_model,
        source_nodes=source_nodes,
        node_output_resolver=DataflowPlanNodeOutputDataSetResolver(
            column_association_resolver=DefaultColumnAssociationResolver(semantic_model),
            semantic_model=semantic_model,
            time_spine_source=time_spine_source,
        ),
    )


@dataclass(frozen=True)
class ConsistentIdObjectRepository:
    """Stores all objects that should have consistent IDs in tests."""

    simple_model_data_sets: OrderedDict[str, DataSourceDataSet]
    simple_model_read_nodes: OrderedDict[str, ReadSqlSourceNode[DataSourceDataSet]]
    simple_model_source_nodes: Sequence[BaseOutput[DataSourceDataSet]]

    multihop_model_read_nodes: OrderedDict[str, ReadSqlSourceNode[DataSourceDataSet]]
    multihop_model_source_nodes: Sequence[BaseOutput[DataSourceDataSet]]

    scd_model_data_sets: OrderedDict[str, DataSourceDataSet]
    scd_model_read_nodes: OrderedDict[str, ReadSqlSourceNode[DataSourceDataSet]]
    scd_model_source_nodes: Sequence[BaseOutput[DataSourceDataSet]]


@pytest.fixture(scope="session")
def consistent_id_object_repository(
    simple_semantic_model: SemanticModel,
    multi_hop_join_semantic_model: SemanticModel,
    scd_semantic_model: SemanticModel,
) -> ConsistentIdObjectRepository:  # noqa: D
    """Create objects that have incremental numeric IDs with a consistent value.

    This should use IDs with a high enough value so that when other tests run with ID generators set to 0 at the start
    of the test and create objects, there is no overlap in the IDs.
    """

    with patch_id_generators_helper(start_value=IdNumberSpace.CONSISTENT_ID_REPOSITORY):
        sm_data_sets = create_data_sets(simple_semantic_model)
        multihop_data_sets = create_data_sets(multi_hop_join_semantic_model)
        scd_data_sets = create_data_sets(scd_semantic_model)

        return ConsistentIdObjectRepository(
            simple_model_data_sets=sm_data_sets,
            simple_model_read_nodes=_data_set_to_read_nodes(sm_data_sets),
            simple_model_source_nodes=_data_set_to_source_nodes(simple_semantic_model, sm_data_sets),
            multihop_model_read_nodes=_data_set_to_read_nodes(multihop_data_sets),
            multihop_model_source_nodes=_data_set_to_source_nodes(multi_hop_join_semantic_model, multihop_data_sets),
            scd_model_data_sets=scd_data_sets,
            scd_model_read_nodes=_data_set_to_read_nodes(scd_data_sets),
            scd_model_source_nodes=_data_set_to_source_nodes(
                semantic_model=scd_semantic_model, data_sets=scd_data_sets
            ),
        )


def create_data_sets(multihop_semantic_model: SemanticModel) -> OrderedDict[str, DataSourceDataSet]:
    """Convert the DataSources in the model to SqlDataSets.

    Key is the name of the data source, value is the associated data set.
    """
    # Use ordered dict and sort by name to get consistency when running tests.
    data_sets = OrderedDict()
    data_sources: List[DataSource] = multihop_semantic_model.user_configured_model.data_sources
    data_sources.sort(key=lambda x: x.name)

    converter = DataSourceToDataSetConverter(
        column_association_resolver=DefaultColumnAssociationResolver(multihop_semantic_model)
    )

    for data_source in data_sources:
        data_sets[data_source.name] = converter.create_sql_source_data_set(data_source)

    return data_sets


@pytest.fixture(scope="session")
def template_mapping(mf_test_session_state: MetricFlowTestSessionState) -> Dict[str, str]:
    """Mapping for template variables in the model YAML files."""
    return {"source_schema": mf_test_session_state.mf_source_schema}


@pytest.fixture(scope="session")
def simple_semantic_model_non_ds(template_mapping: Dict[str, str]) -> SemanticModel:  # noqa: D
    model_build_result = parse_directory_of_yaml_files_to_model(
        os.path.join(os.path.dirname(__file__), "model_yamls/non_ds_model"), template_mapping=template_mapping
    )
    return SemanticModel(model_build_result.model)


@pytest.fixture(scope="session")
def simple_semantic_model(template_mapping: Dict[str, str]) -> SemanticModel:  # noqa: D
    model_build_result = parse_directory_of_yaml_files_to_model(
        os.path.join(os.path.dirname(__file__), "model_yamls/simple_model"), template_mapping=template_mapping
    )
    return SemanticModel(model_build_result.model)


@pytest.fixture(scope="session")
def multi_hop_join_semantic_model(template_mapping: Dict[str, str]) -> SemanticModel:  # noqa: D
    model_build_result = parse_directory_of_yaml_files_to_model(
        os.path.join(os.path.dirname(__file__), "model_yamls/multi_hop_join_model/partitioned_data_sources"),
        template_mapping=template_mapping,
    )
    return SemanticModel(model_build_result.model)


@pytest.fixture(scope="session")
def unpartitioned_multi_hop_join_semantic_model(template_mapping: Dict[str, str]) -> SemanticModel:  # noqa: D
    model_build_result = parse_directory_of_yaml_files_to_model(
        os.path.join(os.path.dirname(__file__), "model_yamls/multi_hop_join_model/unpartitioned_data_sources"),
        template_mapping=template_mapping,
    )
    return SemanticModel(model_build_result.model)


@pytest.fixture(scope="session")
def simple_user_configured_model(template_mapping: Dict[str, str]) -> UserConfiguredModel:
    """Model used for many tests."""

    model_build_result = parse_directory_of_yaml_files_to_model(
        os.path.join(os.path.dirname(__file__), "model_yamls/simple_model"), template_mapping=template_mapping
    )
    return model_build_result.model


@pytest.fixture(scope="session")
def simple_model__with_primary_transforms(template_mapping: Dict[str, str]) -> UserConfiguredModel:
    """Model used for tests pre-transformations."""

    model_build_result = parse_directory_of_yaml_files_to_model(
        os.path.join(os.path.dirname(__file__), "model_yamls/simple_model"),
        template_mapping=template_mapping,
        apply_transformations=False,
    )
    transformed_model = ModelTransformer.transform(
        model=model_build_result.model, ordered_rule_sequences=(ModelTransformer.PRIMARY_RULES,)
    )
    return transformed_model


@pytest.fixture(scope="session")
def extended_date_semantic_model(template_mapping: Dict[str, str]) -> SemanticModel:  # noqa: D
    model_build_result = parse_directory_of_yaml_files_to_model(
        os.path.join(os.path.dirname(__file__), "model_yamls/extended_date_model"),
        template_mapping=template_mapping,
    )
    return SemanticModel(model_build_result.model)


@pytest.fixture(scope="session")
def scd_semantic_model(template_mapping: Dict[str, str]) -> SemanticModel:
    """Initialize semantic model for SCD tests"""
    model_build_result = parse_directory_of_yaml_files_to_model(
        os.path.join(os.path.dirname(__file__), "model_yamls/scd_model"), template_mapping=template_mapping
    )
    return SemanticModel(model_build_result.model)


@pytest.fixture(scope="session")
def data_warehouse_validation_model(template_mapping: Dict[str, str]) -> UserConfiguredModel:
    """Model used for data warehouse validation tests"""

    model_build_result = parse_directory_of_yaml_files_to_model(
        os.path.join(os.path.dirname(__file__), "model_yamls/data_warehouse_validation_model"),
        template_mapping=template_mapping,
    )
    return model_build_result.model
