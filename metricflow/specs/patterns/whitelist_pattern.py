from __future__ import annotations

from typing import Sequence

from metricflow.specs.patterns.spec_pattern import SpecPattern
from metricflow.specs.specs import InstanceSpec


class WhitelistSpecPatten(SpecPattern):
    """A spec pattern that matches based on a configured whitelist of specs.

    This is useful for filtering possible group-by-items to ones valid for a query.
    """

    def __init__(self, whitelisted_specs: Sequence[InstanceSpec]) -> None:  # noqa: D
        self._whitelisted_specs = set(whitelisted_specs)

    def match(self, candidate_specs: Sequence[InstanceSpec]) -> Sequence[InstanceSpec]:
        return tuple(spec for spec in candidate_specs if spec in self._whitelisted_specs)
