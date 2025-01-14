#!/usr/bin/env python3
# Copyright 2024 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Charmed Gubernator."""
import socket

import opentelemetry
import ops
from charms.tempo_coordinator_k8s.v0.charm_tracing import charm_tracing
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer, charm_tracing_config
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer


def kubernetes_service_dns_name():
    """Return the service DNS name for this application.

    This hostname is resolved to a set of ip addresses within the kubernetes cluster.
    Gubernator is designed so that any node can be called with any request, and it
    will handle the synchronisation internally.
    """
    pod_hostname = socket.getfqdn()
    _unit, service_dns_name = pod_hostname.split(".", 1)
    # FIXME: not sure about this, it could be customised by k8s admin
    assert service_dns_name.endswith(".local")
    return service_dns_name


@charm_tracing(
    tracing_endpoint="tracing_endpoint",
)
class HexanatorCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self.ingress = IngressPerAppRequirer(self, port=80, strip_prefix=True)
        self.tracing = TracingEndpointRequirer(self)
        self.tracing_endpoint, self.server_cert = charm_tracing_config(self.tracing)

        self.framework.observe(self.on["gubernator"].pebble_ready, self._on_pebble_ready)
        self.framework.observe(self.on["rate-limit"].relation_created, self._on_relation)
        self.tracer = opentelemetry.trace.get_tracer("hexanator")

    def _on_pebble_ready(self, event: ops.PebbleReadyEvent):
        """Kick off Pebble services.

        The `gubernator` service is configured and enabled in the `rockcraft.yaml` file.
        Pebble starts with `--on-hold` in the workload container, release it.
        """
        with self.tracer.start_as_current_span("pebble ready"):
            event.workload.replan()
            self.unit.status = ops.ActiveStatus()

    def _on_relation(self, event: ops.RelationCreatedEvent):
        """Publish the service DNS name to the rate limit user app."""
        with self.tracer.start_as_current_span("on relation"):
            if self.unit.is_leader():
                event.relation.data[self.app]["url"] = f"http://{kubernetes_service_dns_name()}/"


if __name__ == "__main__":  # pragma: nocover
    ops.main(HexanatorCharm)  # type: ignore
