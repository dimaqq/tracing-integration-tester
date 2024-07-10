from unittest.mock import ANY

import ops
import pytest
from scenario import Context, Container, Relation, State

from charm import HexanatorCharm

META = {
    "name": "hexanator",
    "requires": {
        "ingress": {
            "interface": "ingress"
        }
    },
    "containers": {
        "gubernator": {}
    },

}


def test_startup():
    ctx = Context(HexanatorCharm, meta=META)
    container = Container(name="gubernator", can_connect=True)
    relation=Relation(endpoint="ingress", interface="ingress", remote_app_name="ingress")
    state = State( leader=True, relations=[relation], containers=[container])

    state = ctx.run(ctx.on.start(), state)
    state = ctx.run(ctx.on.pebble_ready(container), state)
    state = ctx.run(ctx.on.relation_joined(relation), state)

    assert state.unit_status == ops.ActiveStatus()
    assert relation.local_app_data == {"model": ANY, "name": '"hexanator"', "port": "80", "strip-prefix": "true"}
