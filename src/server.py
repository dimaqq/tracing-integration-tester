#!/usr/bin/env python3
# Copyright 2025 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Tracing Integration Tester Server."""
import contextlib
import json
import logging
import random
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


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

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    for i in range(10):
        port = random.randint(1025, 10000)
        try:
            server = DualStackServer(("", port), AlwaysOKHandler)
            break
        except OSError:
            pass

    logging.info("Starting HTTP server on %s", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down.")
        server.server_close()
