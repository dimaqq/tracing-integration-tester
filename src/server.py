#!/usr/bin/env python3
# Copyright 2025 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Tracing Integration Tester Server."""
from __future__ import annotations

import contextlib
import json
import logging
import os
import pathlib
import random
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

prefix = pathlib.Path("/tmp" if os.geteuid() else "/var/run")
datadir = prefix / "server.data"


class Recorder(BaseHTTPRequestHandler):
    """Record any incoming HTTP request."""
    name: str

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

        print(content or body)
        r["body"] = str(body)
        r["json"] = content
        print(r)
        assert datadir
        (datadir / str(time.time())).write_text(json.dumps(r))

        # send 200 OK
        self.send_response(200)
        self.end_headers()

    def do_GET(self):  # noqa: N802
        if self.path == "internal-health-check":
            self.send_response(200)
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


class DualStackServer(ThreadingHTTPServer):
    """Copied from Python http module."""
    def server_bind(self):
        # suppress exception when protocol is IPv4
        #with contextlib.suppress(Exception):
        try:
            self.socket.setsockopt(
                socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except Exception:
            logging.exception("ignoramus")
        return super().server_bind()


def nohup(name: str):
    """Start a named server like `nohup foo &`."""
    subprocess.Popen([sys.executable, pathlib.Path(__file__).resolve(), name], stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)


def ensure_started(name: str) -> None:
    """Make sure that the named server is running."""
    pid: int|None = None

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

    for i in range(10):
        time.sleep(1)
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
                break
            except OSError:
                # Not ready to serve
                continue
    else:
        raise TimeoutError(f"No live server {name=} after 10 seconds")


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

        os.kill(pid, signal.SIGTERM)

        try:
            time.sleep(1)
            os.kill(pid, 0)
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
    with sqlite3.connect(prefix / "server.db", isolation_level=None, timeout=5) as conn:
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
            """)
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

    for i in range(10):
        port = random.randint(1025, 10000)
        try:
            server = DualStackServer(("", port), Recorder)
            server.RequestHandlerClass.name = name  # type: ignore
            break
        except OSError:
            pass
    else:
        raise RuntimeError("Could not allocate a port to listen on")

    with tx() as conn:
        conn.execute("UPDATE server SET port=? WHERE name=?", (port, name))

    logging.info(f"Starting {name=} on {port=}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info(f"Shutting down {name=} on {port=}")
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    name = sys.argv[1]
    run(name)
