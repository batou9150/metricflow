import pytest

from dbt_semantic_interfaces.objects.elements.dimension import Dimension, DimensionType, DimensionTypeParams
from metricflow.model.validations.validator_helpers import ModelValidationException
from metricflow.test.model.validations.helpers import semantic_model_with_guaranteed_meta
from dbt_semantic_interfaces.objects.time_granularity import TimeGranularity


@pytest.mark.skip("TODO: Will convert to validation rule")
def test_semantic_model_invalid_sql() -> None:  # noqa:D
    with pytest.raises(ModelValidationException, match=r"Invalid SQL"):
        semantic_model_with_guaranteed_meta(
            name="invalid_sql_source",
            dimensions=[
                Dimension(
                    name="ds",
                    type=DimensionType.TIME,
                    type_params=DimensionTypeParams(
                        time_granularity=TimeGranularity.DAY,
                    ),
                )
            ],
        )