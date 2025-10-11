"""
Network validation tests using RESTCONF.
These tests verify connectivity and data retrieval from network devices.
"""
import os
import json
import pytest
from nornir.core.filter import F
from net.nornir.tasks.show_httpx import restconf_get

# CI/CD skip flag
skip_net = os.getenv("SKIP_NETWORK_TESTS") == "1"

def test_project_structure(project_root_path):
    """Verify expected project structure exists."""
    required_dirs = [
        project_root_path / "net" / "nornir" / "tasks",
        project_root_path / "net" / "nornir" / "inventory",
        project_root_path / "automation" / "lib",
        project_root_path / "logs",
    ]

    for dir_path in required_dirs:
        assert dir_path.exists(), f"Required directory missing: {dir_path}"

    print(f"✓ Project structure validated at {project_root_path}")

@pytest.mark.skipif(skip_net, reason="Skipping network tests in CI")
def test_interfaces_present_and_named(nornir_instance):
    """Validate that RESTCONF can retrieve interfaces and they have required fields."""
    flt = nornir_instance.filter(F(name="cisco_8k-xe"))
    assert flt.inventory.hosts, "No host matched filter 'cisco_8k-xe'"

    # Execute RESTCONF GET
    res = flt.run(task=restconf_get, path="ietf-interfaces:interfaces")

    # Ensure task succeeded
    for host, multi_result in res.items():
        assert not multi_result.failed, f"Task failed for {host}: {multi_result[0].result}"

    # Parse JSON response
    out = next(iter(res.values()))[0].result
    data = json.loads(out)

    # Validate structure
    ifaces = data.get("ietf-interfaces:interfaces", {}).get("interface", [])
    assert isinstance(ifaces, list), "interfaces.interface should be a list"
    assert len(ifaces) > 0, "No interfaces returned - device may be misconfigured"

    # Validate all interfaces have required fields
    assert all("name" in i for i in ifaces), "Some interfaces missing 'name' field"

    print(f"✓ Retrieved {len(ifaces)} interfaces")

@pytest.mark.skipif(skip_net, reason="Skipping network tests in CI")
def test_interface_operational_data(nornir_instance):
    """Verify operational status is retrievable and valid."""
    flt = nornir_instance.filter(F(name="cisco_8k-xe"))
    assert flt.inventory.hosts, "No host matched"

    res = flt.run(task=restconf_get, path="openconfig-interfaces:interfaces")

    out = next(iter(res.values()))[0].result
    data = json.loads(out)
    ifaces = data.get("openconfig-interfaces:interfaces", {}).get("interface", [])

    # At least one interface should be operational
    oper_up = [i for i in ifaces if i.get("state").get("oper-status") == "UP"]
    assert len(oper_up) > 0, "No interfaces in 'up' operational state"

    print(f"✓ Found {len(oper_up)}/{len(ifaces)} interfaces operationally up")


@pytest.mark.skipif(skip_net, reason="Skipping network tests in CI")
def test_restconf_error_handling(nornir_instance):
    """Test that invalid paths return proper errors without crashing."""
    flt = nornir_instance.filter(F(name="cisco_8k-xe"))

    # Intentionally bad path
    res = flt.run(task=restconf_get, path="invalid:nonexistent-path")

    # Should fail gracefully, not crash
    for host, multi_result in res.items():
        result = multi_result[0]
        assert result.failed, "Expected task to fail for invalid path"
        assert "404" in str(result.result) or "400" in str(result.result), \
            "Expected HTTP 404/400 error"

    print("✓ Error handling working correctly")

@pytest.mark.skipif(skip_net, reason="Skipping network tests in CI")
def test_client_reuse(nornir_instance):
    """Verify httpx client is reused across multiple calls."""
    flt = nornir_instance.filter(F(name="cisco_8k-xe"))

    # First call - creates client
    res1 = flt.run(task=restconf_get, path="openconfig-interfaces:interfaces")
    assert not res1.failed

    # Second call - should reuse client
    res2 = flt.run(task=restconf_get, path="openconfig-interfaces:interfaces")
    # Note: This might fail on some devices if interfaces-state isn't supported

    # Check that client was stored (implies reuse)
    host = next(iter(flt.inventory.hosts.values()))
    assert "_restconf_httpx" in host.data, "Client store not found in host.data"
    assert "client" in host.data["_restconf_httpx"], "Client not stored"

    print("✓ Client reuse mechanism working")

@pytest.mark.skipif(skip_net, reason="Skipping network tests in CI")
def test_response_time_reasonable(nornir_instance):
    """Basic performance check - RESTCONF should respond within reasonable time."""
    import time

    flt = nornir_instance.filter(F(name="cisco_8k-xe"))

    start = time.time()
    res = flt.run(task=restconf_get, path="openconfig-interfaces:interfaces")
    elapsed = time.time() - start

    assert not res.failed, "Task failed"
    assert elapsed < 10.0, f"Request took {elapsed:.2f}s - exceeds 10s threshold"

    print(f"✓ Response time: {elapsed:.2f}s")

@pytest.mark.skipif(skip_net, reason="Skipping network tests in CI")
def test_pre_post_validation_pattern(nornir_instance):
    """Demonstrate safe change pattern: pre-check → (change) → post-check → verify."""
    flt = nornir_instance.filter(F(name="cisco_8k-xe"))

    # PRE-CHECK: Get baseline state
    pre = flt.run(task=restconf_get, path="openconfig-interfaces:interfaces")
    pre_data = json.loads(next(iter(pre.values()))[0].result)
    pre_ifaces = pre_data.get("openconfig-interfaces:interfaces", {}).get("interface", [])
    pre_count = len(pre_ifaces)

    # CHANGE: (simulated - no actual change in this test)
    # In real scenario: flt.run(task=restconf_patch, path=..., payload=...)

    # POST-CHECK: Verify state after change
    post = flt.run(task=restconf_get, path="openconfig-interfaces:interfaces")
    post_data = json.loads(next(iter(post.values()))[0].result)
    post_ifaces = post_data.get("openconfig-interfaces:interfaces", {}).get("interface", [])
    post_count = len(post_ifaces)

    # VERIFY: State should be consistent (since we didn't actually change anything)
    assert pre_count == post_count, \
        f"Interface count mismatch: pre={pre_count}, post={post_count}"

    print(f"✓ Pre/post validation pattern working (verified {pre_count} interfaces)")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])