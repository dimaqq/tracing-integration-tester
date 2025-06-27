import json
from unittest.mock import ANY

import ops
import pytest
from ops.testing import Context, Relation, State

from charm import TracingIntegrationTester


def default_pebble_layer() -> ops.pebble.LayerDict:
    import yaml

    tmp = yaml.safe_load(open("rockcraft.yaml").read())
    assert tmp["services"]["gubernator"]["startup"] == "enabled"
    return tmp


@pytest.fixture
def ctx():
    return Context(TracingIntegrationTester)


@pytest.fixture
def initial_state():
    tracing = Relation("tracing", id=0, interface="tracing", remote_app_name="tracing")
    return State(leader=True, relations={tracing})  # type: ignore


def test_tracing(ctx, initial_state):
    relation = initial_state.get_relation(0)
    result_state = ctx.run(ctx.on.relation_joined(relation), initial_state)
    relation = result_state.get_relation(0)
    assert set(relation.local_app_data) == {"receivers"}
    assert json.loads(relation.local_app_data["receivers"]) == [
        {
            "protocol": {"name": "otlp_http", "type": "http"},
            "url": ANY,
        }
    ]
    assert json.loads(relation.local_app_data["receivers"])[0]["url"].startswith("http://")
