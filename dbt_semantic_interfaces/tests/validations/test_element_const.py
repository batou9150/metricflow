import copy
import pytest
from typing import Tuple

from dbt_semantic_interfaces.model_validator import ModelValidator
from dbt_semantic_interfaces.objects.data_source import DataSource
from dbt_semantic_interfaces.objects.elements.dimension import Dimension, DimensionType
from dbt_semantic_interfaces.objects.user_configured_model import UserConfiguredModel
from dbt_semantic_interfaces.validations.element_const import ElementConsistencyRule
from dbt_semantic_interfaces.validations.validator_helpers import DataSourceElementType, ModelValidationException
from dbt_semantic_interfaces.test_utils import find_data_source_with


def _categorical_dimensions(data_source: DataSource) -> Tuple[Dimension, ...]:
    return tuple(dim for dim in data_source.dimensions if dim.type == DimensionType.CATEGORICAL)


def test_cross_element_names(simple_model__with_primary_transforms: UserConfiguredModel) -> None:  # noqa:D
    model = copy.deepcopy(simple_model__with_primary_transforms)

    # ensure we have a usable data source for the test
    usable_ds, usable_ds_index = find_data_source_with(
        model,
        lambda data_source: len(data_source.measures) > 0
        and len(data_source.identifiers) > 0
        and len(_categorical_dimensions(data_source=data_source)) > 0,
    )

    measure_reference = usable_ds.measures[0].reference
    # If the matching dimension is a time dimension we can accidentally create two primary time dimensions, and then
    # the validation will throw a different error and fail the test
    dimension_reference = _categorical_dimensions(data_source=usable_ds)[0].reference

    ds_measure_x_dimension = copy.deepcopy(usable_ds)
    ds_measure_x_identifier = copy.deepcopy(usable_ds)
    ds_dimension_x_identifier = copy.deepcopy(usable_ds)

    # We update the matching categorical dimension by reference for convenience
    ds_measure_x_dimension.get_dimension(dimension_reference).name = measure_reference.element_name
    ds_measure_x_identifier.identifiers[0].name = measure_reference.element_name
    ds_dimension_x_identifier.identifiers[0].name = dimension_reference.element_name

    model.data_sources[usable_ds_index] = ds_measure_x_dimension
    with pytest.raises(
        ModelValidationException,
        match=(
            f"element `{measure_reference.element_name}` is of type {DataSourceElementType.DIMENSION}, but it is used as "
            f"types .*?DataSourceElementType.DIMENSION.*?DataSourceElementType.MEASURE.*? across the model"
        ),
    ):
        ModelValidator([ElementConsistencyRule()]).checked_validations(model)

    model.data_sources[usable_ds_index] = ds_measure_x_identifier
    with pytest.raises(
        ModelValidationException,
        match=(
            f"element `{measure_reference.element_name}` is of type {DataSourceElementType.ENTITY}, but it is used as "
            f"types .*?DataSourceElementType.ENTITY.*?DataSourceElementType.MEASURE.*? across the model"
        ),
    ):
        ModelValidator([ElementConsistencyRule()]).checked_validations(model)

    model.data_sources[usable_ds_index] = ds_dimension_x_identifier
    with pytest.raises(
        ModelValidationException,
        match=(
            f"element `{dimension_reference.element_name}` is of type {DataSourceElementType.DIMENSION}, but it is used as "
            f"types .*?DataSourceElementType.DIMENSION.*?DataSourceElementType.ENTITY.*? across the model"
        ),
    ):
        ModelValidator([ElementConsistencyRule()]).checked_validations(model)
