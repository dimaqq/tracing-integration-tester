#!/usr/bin/env python3
# Copyright 2025 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Tracing Integration Tester."""

import json
import logging
import socket
import typing

import ops

import server


class TracingIntegrationTester(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        self.framework.observe(self.on.config_changed, self.reconcile)
        self.framework.observe(self.on.tracing_relation_created, self.reconcile)
        self.framework.observe(self.on.tracing_relation_joined, self.reconcile)
        self.framework.observe(self.on.tracing_relation_departed, self.reconcile)
        self.framework.observe(self.on.tracing_relation_broken, self.reconcile)

        self.framework.observe(self.on.get_traces_action, self.get_traces_action)

    def reconcile(self, event: typing.Any):
        if not self.unit.is_leader():
            logging.warning("This app should not be scaled out.")
            return

        host = socket.getfqdn()
        server.init_db()
        servers: set[str] = set()
        for rel in self.model.relations["tracing"]:
            if not rel.app.name:
                logging.warning("FIXME %s", [event, rel, rel.app, rel.app.name])
                continue
            servers.add(rel.app.name)
            port = server.ensure_started(rel.app.name)
            rel.data[self.app]["receivers"] = json.dumps(
                [
                    {
                        "protocol": {"name": "otlp_http", "type": "http"},
                        "url": f"http://{host}:{port}/",
                    }
                ]
            )

        for redundant in server.list_server_names() - servers:
            server.ensure_stopped(redundant)

        self.model.app.status = ops.ActiveStatus(str(servers))

    def get_traces_action(self, event: ops.ActionEvent):
        # FIXME implement filter by start, end, application
        # event.params ...
        traces = [str(p) for p in server.datadir.glob("*.json")]
        event.set_results({"traces": json.dumps(traces)})


if __name__ == "__main__":
    ops.main(TracingIntegrationTester)
