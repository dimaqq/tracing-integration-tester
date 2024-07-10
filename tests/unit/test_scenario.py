import ops
import pytest
import scenario

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
    ctx = scenario.Context(HexanatorCharm, meta=META)
    in_ = scenario.State(
        leader=True,
        relations=[scenario.Relation(endpoint="ingress", interface="ingress", remote_app_name="ingress")],
        containers=[scenario.Container(name="gubernator", can_connect=True)],
    )
    out = ctx.run(ctx.on.start(), in_)
    out = ctx.run(ctx.on.pebble_ready(next(iter(in_.containers))), out)
    assert out.unit_status == ops.ActiveStatus()
