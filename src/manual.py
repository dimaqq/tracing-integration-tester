#!/usr/bin/env python3
# Copyright 2025 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Fixme don't merge this."""
from __future__ import annotations

import time

from server import ensure_started, ensure_stopped, init_db

init_db()
ensure_started("aa")
time.sleep(0.1)
ensure_started("aa")
time.sleep(0.1)
ensure_started("aa")
time.sleep(0.1)
ensure_started("bb")
time.sleep(0.1)

ensure_stopped("bb")
time.sleep(0.1)
ensure_stopped("aa")
time.sleep(0.1)
