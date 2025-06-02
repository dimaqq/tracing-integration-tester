#!/usr/bin/env python3
# Copyright 2025 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Tracing Integration Tester."""

import json
import logging
import socket
import typing

import ops

from . import server


class TracingIntegrationTester(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self.framework.observe(self.on.config_changed, self.reconcile)
        self.framework.observe(self.on.tracing_relation_created, self.reconcile)
        self.framework.observe(self.on.tracing_relation_broken, self.reconcile)

    def reconcile(self, event: typing.Any):
        host = socket.getfqdn()
        if not self.unit.is_leader():
            logging.warning("This app should not be scaled out.")
            return

        requested: set[str] = set()
        for rel in self.model.relations["tracing"]:
            if not rel.app.name:
                logging.warning("FIXME %s", [event, rel, rel.app, rel.app.name])
                continue
            requested.add(rel.app.name)
            port = server.ensure_started(rel.app.name)
            rel.data[self.app]["foo"] = json.dumps(
                {
                    "receivers": [
                        {
                            "protocol": {"name": "otlp_http", "type": "http"},
                            "url": f"http//{host}:{port}/v1/traces",
                        },
                    ]
                }
            )

        for redundant in server.list_server_names() - requested:
            server.ensure_stopped(redundant)

        print(f"\n\n{event}\n\n")


if __name__ == "__main__":
    ops.main(TracingIntegrationTester)
