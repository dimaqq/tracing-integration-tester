from unittest.mock import ANY

import ops
from charm import HexanatorCharm
from scenario import Container, Context, Relation, State


def default_pebble_layer() -> dict:
    import yaml
    tmp = yaml.safe_load(open("rockcraft.yaml").read())
    assert tmp["services"]["gubernator"]["startup"] == "enabled"
    return tmp


def test_startup():
    ctx = Context(HexanatorCharm)
    pebble_layers = {"default": ops.pebble.Layer(raw=default_pebble_layer())}  # type: ignore
    container = Container(name="gubernator", can_connect=True, layers=pebble_layers)
    relation=Relation(endpoint="ingress", interface="ingress", remote_app_name="ingress")
    state = State( leader=True, relations={relation}, containers={container})  # type: ignore

    state = ctx.run(ctx.on.start(), state)
    state = ctx.run(ctx.on.pebble_ready(container), state)
    state = ctx.run(ctx.on.relation_joined(relation), state)

    assert state.unit_status == ops.ActiveStatus()
    assert relation.local_app_data == {"model": ANY, "name": '"hexanator"', "port": "80", "strip-prefix": "true"}
    assert list(state.containers)[0].service_status["gubernator"] == ops.pebble.ServiceStatus.ACTIVE
