import os
import pytest

skip_net = os.environ.get("SKIP_NETWORK_TESTS") == "1"

@pytest.mark.skipif(skip_net, reason="Skipping network tests in CI by default")
def test_placeholder_network():
    # This is where you'd call into Nornir/Batfish/pyATS.
    assert True
