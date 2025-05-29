#!/usr/bin/env python3
# Copyright 2025 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Tracing Integration Tester."""
import typing

import ops


class TracingIntegrationTester(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self.framework.observe(self.on.start, self.dummy)
        self.framework.observe(self.on.upgrade_charm, self.dummy)
        self.framework.observe(self.on.config_changed, self.dummy)

    def dummy(self, event: typing.Any):
        """Do it all."""
        print(f"\n\n{event}\n\n")
