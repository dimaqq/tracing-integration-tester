#!/usr/bin/env python3
# Copyright 2024 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Charmed Gubernator."""

import ops
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer


class HexanatorCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.ingress = IngressPerAppRequirer(self, port=80, strip_prefix=True)
        self.framework.observe(self.on['gubernator'].pebble_ready, self._on_gubernator_pebble_ready)

    def _on_gubernator_pebble_ready(self, event: ops.PebbleReadyEvent):
        """Kick off Pebble services.

        The `gubernator` service is configured and enabled in the `rockcraft.yaml` file.
        Pebble starts with `--on-hold` in the workload container, release it.
        """
        event.workload.replan()
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(HexanatorCharm)  # type: ignore
