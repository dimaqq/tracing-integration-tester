#!/usr/bin/env python3
# Copyright 2025 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Fixme don't merge this."""

from __future__ import annotations

import logging
import pathlib
import sys

from server import ensure_started, ensure_stopped, init_db, list_server_names


def main(input_file):
    """Keep a set of servers up."""
    init_db()
    running = list_server_names()
    wanted = {w for w in input_file.read_text().split() if w}
    for destroy in running - wanted:
        ensure_stopped(destroy)
    portmap = {name: ensure_started(name) for name in wanted}
    input_file.with_suffix(".out").write_text(
        "\n".join(f"{k}: http://localhost:{v}/" for k, v in portmap.items())
    )
    for name, port in portmap.items():
        pathlib.Path(f"{name}.url").write_text(f"http://localhost:{port}/")


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    if not sys.argv[1:]:
        print(f"""Usage: {sys.argv[0]} an_input_file
    Where `an_input_file` lists required server names one per line.""")
        exit(1)
    main(pathlib.Path(sys.argv[1]))
