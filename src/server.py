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
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

datadir: pathlib.Path | None = None
prefix = pathlib.Path("/tmp" if os.geteuid() else "/var/run")


class AlwaysOKHandler(BaseHTTPRequestHandler):
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

    def do_GET(self):
        return self.respond("GET")

    def do_PUT(self):
        return self.respond("PUT")

    def do_HEAD(self):
        return self.respond("HEAD")

    def do_POST(self):
        return self.respond("POST")

    def do_PATCH(self):
        return self.respond("PATCH")

    def do_DELETE(self):
        return self.respond("DELETE")

    def do_OPTIONS(self):
        return self.respond("OPTIONS")

    # FIXME suppress the default stdout logging
    def log_message(self, format, *args):
        pass

def foo():
    addr = ("", 8080)  # all interfaces, port 8080
    if socket.has_dualstack_ipv6():
        s = socket.create_server(addr, family=socket.AF_INET6, dualstack_ipv6=True)
    else:
        s = socket.create_server(addr)

# From Python
class DualStackServer(ThreadingHTTPServer):
    def server_bind(self):
        # suppress exception when protocol is IPv4
        with contextlib.suppress(Exception):
            self.socket.setsockopt(
                socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()


def nohup(name: str):
    subprocess.Popen([sys.executable, pathlib.Path(__file__).resolve(), name], stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)


def starting(name: str) -> bool:
    ...


def started(name: str) -> tuple[int, pathlib.Path]:
    pidfile = prefix / f"tracing-integration-tester-{ name }.pid"
    portfile = prefix / f"tracing-integration-tester-{ name }.port"
    datadir = prefix / f"tracing-integration-tester-{ name }.data"

    pid = int(pidfile.read_text().strip())
    os.kill(pid, 0)
    port = int(portfile.read_text().strip())

    assert datadir.is_dir()

    return port, datadir


def start_server(name: str) -> tuple[int, pathlib.Path]:
    pidfile = prefix / f"tracing-integration-tester-{ name }.pid"
    portfile = prefix / f"tracing-integration-tester-{ name }.port"
    datadir = prefix / f"tracing-integration-tester-{ name }.data"

    nohup(name)

    for i in range(10):
        time.sleep(1)
        try:
            pid = int(pidfile.read_text().strip())
            os.kill(pid, 0)
            port = int(portfile.read_text().strip())
            break
        except Exception:
            pass
    else:
        raise TimeoutError(f"No live server {name=} after 10 seconds")

    return port, datadir


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    self = os.getpid()
    name = sys.argv[1]
    pidfile = prefix / f"tracing-integration-tester-{ name }.pid"
    portfile = prefix / f"tracing-integration-tester-{ name }.port"
    datadir = prefix / f"tracing-integration-tester-{ name }.data"
    try:
        pid = int(pidfile.read_text().strip())
        os.kill(pid, 0)
        raise SystemExit(f"Server for {name=} is still running as {pid=}")
    except Exception:
        pass
    # While this is technically racey, we are relying on the caller not to flood us here.
    try:
        portfile.unlink()
    except FileNotFoundError:
        pass
    # Here as well.
    pidfile.write_text(f"{self}\n")

    for i in range(10):
        port = random.randint(1025, 10000)
        try:
            server = DualStackServer(("", port), AlwaysOKHandler)
            break
        except OSError:
            pass
    else:
        raise RuntimeError("Could not allocate a port to listen on")

    portfile.write_text(f"{ port }\n")
    logging.info("Starting HTTP server for %s on %s", name, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down.")
        server.server_close()
