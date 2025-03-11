#!/usr/bin/env python3
# Copyright 2024 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Charmed Gubernator."""
import logging
import socket

import opentelemetry.trace
import ops
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from ops._tracing.api import Tracing

tracer = opentelemetry.trace.get_tracer(__name__)


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


# @charm_tracing( tracing_endpoint="tracing_endpoint")
class HexanatorCharm(ops.CharmBase):
    """Charm the service."""

    @tracer.start_as_current_span("__init__")
    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        with tracer.start_as_current_span("self.ingress"):
            self.ingress = IngressPerAppRequirer(self, port=80, strip_prefix=True)

        with tracer.start_as_current_span("self.tracing"):
            self.tracing = Tracing(
                self,
                tracing_relation_name="charm-tracing",
                ca_relation_name="send-ca-cert",
            )

        self.framework.observe(self.on["gubernator"].pebble_ready, self._on_pebble_ready)
        self.framework.observe(self.on["rate-limit"].relation_created, self._on_relation)

    def _on_pebble_ready(self, event: ops.PebbleReadyEvent):
        """Kick off Pebble services.

        The `gubernator` service is configured and enabled in the `rockcraft.yaml` file.
        Pebble starts with `--on-hold` in the workload container, release it.
        """
        with tracer.start_as_current_span("pebble is ready, starting guberantor"):
            event.workload.replan()
            self.unit.status = ops.ActiveStatus()

    def _on_relation(self, event: ops.RelationCreatedEvent):
        """Publish the service DNS name to the rate limit user app."""
        with tracer.start_as_current_span("relation changed, stamp our service name"):
            if self.unit.is_leader():
                event.relation.data[self.app]["url"] = f"http://{kubernetes_service_dns_name()}/"
            else:
                logging.debug("I'm not the leader, do nothing")


if __name__ == "__main__":  # pragma: nocover
    ops.main(HexanatorCharm)  # type: ignore
