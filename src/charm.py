#!/usr/bin/env python3
# Copyright 2025 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Tracing Fake."""

import json
import logging
import pathlib
import socket
import typing

import ops

import server


class TracingFake(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        self.framework.observe(self.on.config_changed, self.reconcile)
        self.framework.observe(self.on.tracing_relation_created, self.reconcile)
        self.framework.observe(self.on.tracing_relation_joined, self.reconcile)
        self.framework.observe(self.on.tracing_relation_departed, self.reconcile)
        self.framework.observe(self.on.tracing_relation_broken, self.reconcile)

        self.framework.observe(self.on.list_traces_action, self.list_traces)
        self.framework.observe(self.on.drop_traces_action, self.drop_traces)
        self.framework.observe(self.on.read_trace_action, self.read_trace)

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

    def list_traces(self, event: ops.ActionEvent):
        apps = [a.strip() for a in event.params.get("apps", "").split(",") if a.strip()]
        start = event.params.get("start", float("-inf"))
        end = event.params.get("end", float("inf"))
        paths = [t for t in server.datadir.glob("*.json") if match(t, apps, start, end)]
        event.set_results({"traces": json.dumps([str(p) for p in paths])})

    def drop_traces(self, event: ops.ActionEvent):
        apps = [a.strip() for a in event.params.get("apps", "").split(",") if a.strip()]
        start = event.params.get("start", float("-inf"))
        end = event.params.get("end", float("inf"))
        paths = [t for t in server.datadir.glob("*.json") if match(t, apps, start, end)]
        for path in paths:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        event.set_results({"info": f"Dropped {len(paths)} files."})

    def read_trace(self, event: ops.ActionEvent):
        path = pathlib.Path(event.params["path"])
        try:
            assert path.is_relative_to(server.datadir)
            event.set_results({"content": path.read_text()})
        except Exception as e:
            event.fail(repr(e))


def match(path: pathlib.Path, apps: list[str], start: float, end: float):
    """Determine if a particular trace file matches the filters."""
    try:
        app, ts = path.stem.split("-")
        time = float(ts)
    except Exception:
        logging.warning("Skipping data file %r", path)
        return False

    return start <= time <= end and (app in apps or not apps)


if __name__ == "__main__":
    ops.main(TracingFake)
