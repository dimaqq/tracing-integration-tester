#!/usr/bin/env python3
# Copyright 2024 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Charmed Gubernator."""

import logging

import ops

from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]


class HexanatorCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        # TODO: presumably the lib figures out app name and model name
        # TODO: check if this is the correct port
        self.ingress = IngressPerAppRequirer(self, port=80, strip_prefix=True)
        self.framework.observe(self.on['gubernator'].pebble_ready, self._on_gubernator_pebble_ready)

    def _on_gubernator_pebble_ready(self, event: ops.PebbleReadyEvent):
        """Kick off Pebble services.

        The services are preconfigured in the `rockcraft.yaml` file.
        However, Juju starts Pebble with `--on-hold`.
        Here we release Pebble to do it's work.
        """
        # Get a reference the container attribute on the PebbleReadyEvent
        event.workload.replan()
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(HexanatorCharm)  # type: ignore
