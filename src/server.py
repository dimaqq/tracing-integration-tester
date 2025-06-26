#!/usr/bin/env python3
# Copyright 2025 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Tracing Integration Tester Server."""

from __future__ import annotations

import contextlib
import http.server
import json
import logging
import os
import pathlib
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request

datadir = pathlib.Path("/tmp/server.data")
dbfile = pathlib.Path("/tmp/server.db")


class Recorder(http.server.BaseHTTPRequestHandler):
    """Record any incoming HTTP request."""

    server: DualStackServer  # type: ignore

    def respond(self, method: str):
        r = {}
        # log the request
        r["method"] = self.command
        r["path"] = self.path
        body = b""
        content = None
        try:
            size = int(self.headers["Content-Length"])
            body = self.rfile.read(size)
            content = json.loads(body)
        except Exception as e:
            logging.debug("Doesn't look like JSON to me: %s", e)

        r["body"] = str(body)
        r["json"] = content
        logging.info("%s: %s", self.server.name, r)
        assert datadir
        filename = f"{self.server.name}-{str(time.time())}.json"
        (datadir / filename).write_text(json.dumps(r))

        # send 200 OK
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        if self.path == "/internal-health-check":
            self.send_response(200)
            self.end_headers()
            return
        else:
            return self.respond("GET")

    def do_PUT(self):  # noqa: N802
        return self.respond("PUT")

    def do_HEAD(self):  # noqa: N802
        return self.respond("HEAD")

    def do_POST(self):  # noqa: N802
        return self.respond("POST")

    def do_PATCH(self):  # noqa: N802
        return self.respond("PATCH")

    def do_DELETE(self):  # noqa: N802
        return self.respond("DELETE")

    def do_OPTIONS(self):  # noqa: N802
        return self.respond("OPTIONS")

    # FIXME suppress the default stdout logging
    def log_message(self, format, *args):
        pass


class DualStackServer(http.server.ThreadingHTTPServer):
    """Copied from Python's http.server module."""

    def __init__(self, *args, name: str, **kwargs):
        self.name = name
        addrs = socket.getaddrinfo(None, 0, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE)
        addrs6 = [a for a in addrs if a[0] == socket.AF_INET6]
        self.address_family, _, _, _, address = (addrs6 or addrs)[0]
        # The parent constructor sets self.server_address to our address.
        # The parent class expects an IPv4 tuple,
        # however we suppose both IPv4 and IPv6 tuples in custom server_bind.
        super().__init__(address, *args, **kwargs)  # type: ignore

    def server_bind(self):
        # suppress exception when protocol is IPv4
        with contextlib.suppress(Exception):
            # In case dual-stack is disabled in sysctl, re-enable it
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)

        self.socket.bind(self.server_address)
        self.server_name, self.server_port = self.socket.getsockname()[:2]


def nohup(name: str):
    """Start a named server like `nohup foo &`."""
    logging.info(f"Starting {name=} ...")
    subprocess.Popen(
        [sys.executable, pathlib.Path(__file__).resolve(), name],
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def list_server_names() -> set[str]:
    """Return the set of registered server names."""
    with tx() as conn:
        # FIXME do we care about .up?
        cursor = conn.execute("SELECT name FROM server")
        return {c[0] for c in cursor}


def ensure_started(name: str) -> int:
    """Make sure that the named server is running."""
    pid: int | None = None

    with tx() as conn:
        c = conn.execute("SELECT pid FROM server WHERE name=?", (name,)).fetchone()
        pid = c[0] if c else None
        if pid:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                conn.execute("DELETE FROM server WHERE name=?", (name,))
                pid = None
        else:
            conn.execute("DELETE FROM server WHERE name=?", (name,))

    if not pid:
        with tx() as conn:
            conn.execute("INSERT INTO server (name) VALUES (?)", (name,))
        nohup(name)

    for delay in [2**x for x in range(-4, 3)]:
        time.sleep(delay)
        with tx() as conn:
            c = conn.execute("SELECT pid, port FROM server WHERE name=?", (name,)).fetchone()
            if not c:
                continue
            pid, port = c
            if not pid or not port:
                continue

            try:
                os.kill(pid, 0)
            except ProcessLookupError as e:
                raise SystemError(f"Server {name=} at {pid=} missing") from e

            try:
                urllib.request.urlopen(f"http://localhost:{port}/internal-health-check", timeout=1)
                return port
            except OSError:
                # Not ready to serve
                continue
    else:
        raise TimeoutError(f"No live server {name=} after 8 seconds")


def ensure_stopped(name: str) -> None:
    """Make sure the named server is not running."""
    with tx() as conn:
        c = conn.execute("SELECT pid FROM server WHERE name=?", (name,)).fetchone()
        if not c:
            return
        pid = c[0]

        if not pid:
            # Perhaps the server died before it could record own PID.
            # Or we're racing against ensure_started().
            # Let's assume that names are unique, a single unit is responsible.
            return

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            conn.execute("DELETE FROM server WHERE name=?", (name,))
            return

        logging.info(f"Stopping {name=} ...")
        os.kill(pid, signal.SIGTERM)

        try:
            time.sleep(1)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

        try:
            time.sleep(1)
            os.kill(pid, 0)
            raise RuntimeError(f"Somehow server {name=} is still alive {pid=}")
        except ProcessLookupError:
            conn.execute("DELETE FROM server WHERE name=?", (name,))
            return


@contextlib.contextmanager
def tx():
    """Context manager to set up and tear down an exclusive database transaction."""
    with sqlite3.connect(dbfile, isolation_level=None, timeout=5) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")


def init_db():
    """Set up the database schema."""
    with tx() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS server (
                name TEXT PRIMARY KEY,
                pid INTEGER,
                port INTEGER,
                up BOOLEAN NOT NULL DEFAULT(TRUE)
            )
            """
        )
    datadir.mkdir(exist_ok=True)


def run(name: str):
    """Run the named server."""
    pid = os.getpid()
    with tx() as conn:
        try:
            c = conn.execute("SELECT pid FROM server WHERE name=?", (name,)).fetchone()
            if c:
                os.kill(c[0], 0)
                # Signal was sent, the other process is alive
                raise SystemExit(f"Server for {name=} is still running as {pid=}")
        except Exception:
            pass

        conn.execute("UPDATE server SET pid=?, port=NULL, up=FALSE WHERE name=?", (pid, name))

        server = DualStackServer(Recorder, name=name)
        conn.execute("UPDATE server SET port=? WHERE name=?", (server.server_port, name))

    logging.info(f"Started {server.name=} on {server.server_port=}")
    try:
        server.serve_forever()
    except BaseException:
        logging.info(f"Exited {server.name=} on {server.server_port=}")
        server.server_close()
        raise


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    name = sys.argv[1]
    init_db()
    run(name)
