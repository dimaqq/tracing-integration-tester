# Copyright 2024 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing
import ops
import ops.testing
import pytest

from charm import TracingIntegrationTester


@pytest.fixture
def harness():
    harness = ops.testing.Harness(TracingIntegrationTester)
    harness.begin()
    yield harness
    harness.cleanup()


def test_pebble_ready(harness):
    assert harness.model.unit.status == ops.MaintenanceStatus("")

    harness.container_pebble_ready("gubernator")

    assert harness.model.unit.status == ops.ActiveStatus()


def test_ingress_requirer(harness):
    assert harness.charm.ingress._auto_data == (None, None, 80)
    assert harness.charm.ingress._strip_prefix
