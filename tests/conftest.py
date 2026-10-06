import pytest

from einkaufsagent.eval import DEFAULT_SCENARIOS
from einkaufsagent.scenarios import load_scenarios


@pytest.fixture(scope="session")
def scenarios():
    return {s.id: s for s in load_scenarios(DEFAULT_SCENARIOS)}
