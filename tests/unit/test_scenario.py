from unittest.mock import ANY

import ops
import pytest
from ops.testing import Container, Context, Relation, State

from charm import HexanatorCharm


def default_pebble_layer() -> ops.pebble.LayerDict:
    import yaml

    tmp = yaml.safe_load(open("rockcraft.yaml").read())
    assert tmp["services"]["gubernator"]["startup"] == "enabled"
    return tmp


@pytest.fixture
def ctx():
    return Context(HexanatorCharm)


@pytest.fixture
def initial_state():
    pebble_layers = {"default": ops.pebble.Layer(raw=default_pebble_layer())}
    container = Container("gubernator", can_connect=True, layers=pebble_layers)
    ingress = Relation("ingress", id=0, interface="ingress", remote_app_name="ingress")
    rate_limit = Relation("rate-limit", id=1, interface="http", remote_app_name="user")
    return State(leader=True, relations={ingress, rate_limit}, containers={container})  # type: ignore


def test_startup(ctx, initial_state):
    container = list(initial_state.containers)[0]
    state = ctx.run(ctx.on.pebble_ready(container), initial_state)
    assert state.unit_status == ops.ActiveStatus()
    assert (
        list(state.containers)[0].service_statuses["gubernator"] == ops.pebble.ServiceStatus.ACTIVE
    )


def test_ingress(ctx, initial_state):
    relation = initial_state.get_relation(0)
    result_state = ctx.run(ctx.on.relation_joined(relation), initial_state)
    relation = result_state.get_relation(0)
    assert relation.local_app_data == {
        "model": ANY,
        "name": '"hexanator"',
        "port": "80",
        "strip-prefix": "true",
    }


def test_rate_limit(ctx, initial_state, monkeypatch):
    monkeypatch.setattr(
        "socket.getfqdn", lambda: "hexanator-0.hexanator-endpoints.mymodel.svc.cluster.local"
    )
    relation = initial_state.get_relation(1)
    result_state = ctx.run(ctx.on.relation_created(relation), initial_state)
    relation = result_state.get_relation(1)
    assert relation.local_app_data == {
        "url": "http://hexanator-endpoints.mymodel.svc.cluster.local/"
    }
