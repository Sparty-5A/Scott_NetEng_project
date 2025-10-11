import json
import httpx
from typing import Any, Dict
from nornir.core.task import Task, Result
from loguru import logger

HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}

_STORE_KEY = "_restconf_httpx"  # where we keep per-host client in host.data


def _get_store(task: Task) -> Dict[str, Any]:
    """Ensure a dedicated namespace in host.data"""
    store = task.host.data.get(_STORE_KEY)
    if store is None:
        logger.debug(f"[{task.host.name}] Initializing store key '{_STORE_KEY}'")
        store = {}
        task.host.data[_STORE_KEY] = store
    return store


def _get_client(task: Task) -> httpx.Client:
    store = _get_store(task)
    client = store.get("client")

    if client:
        if client.is_closed:  # ← Add this check
            logger.debug(f"[{task.host.name}] Client was closed, creating new one")
            store.pop("client", None)
        else:
            logger.debug(f"[{task.host.name}] Reusing existing httpx.Client")
            return client

    # Extract RESTCONF config from host data
    rc: Dict[str, Any] = task.host.data.get("restconf", {})
    base = rc.get("base_url")
    user = rc.get("username")
    pwd = rc.get("password")
    verify = rc.get("verify_ssl", True)

    logger.debug(f"[{task.host.name}] RESTCONF config: base_url={base}, username={user}, verify_ssl={verify}")

    if not base or not user or not pwd:
        logger.error(f"[{task.host.name}] Missing required RESTCONF credentials in host data")
        raise ValueError("Missing restconf.base_url/username/password in host data")

    # Create new client
    logger.debug(f"[{task.host.name}] Creating new httpx.Client with base_url={base}")
    client = httpx.Client(
        base_url=base.rstrip("/"),
        auth=(user, pwd),  # Note: password not logged (security)
        headers=HEADERS,
        verify=verify,
        timeout=30.0  # Added explicit timeout
    )
    store["client"] = client
    logger.debug(f"[{task.host.name}] httpx.Client created and stored")
    return client

def _pretty_json(body: Any) -> str:
    """Format JSON for display"""
    try:
        return json.dumps(body, indent=2)
    except Exception as e:
        logger.debug(f"JSON formatting failed: {e}, returning raw string")
        return str(body)


def restconf_get(task: Task, path: str) -> Result:
    """Execute RESTCONF GET request"""
    logger.debug(f"[{task.host.name}] Starting RESTCONF GET for path: {path}")

    try:
        client = _get_client(task)
    except ValueError as e:
        logger.error(f"[{task.host.name}] Failed to get client: {e}")
        return Result(host=task.host, failed=True, result=str(e))

    url = f"/data/{path.strip('/')}"
    logger.debug(f"[{task.host.name}] Full URL: {client.base_url}{url}")

    try:
        logger.debug(f"[{task.host.name}] Sending GET request...")
        resp = client.get(url)
        logger.debug(f"[{task.host.name}] Response status: {resp.status_code}")
        logger.debug(f"[{task.host.name}] Response headers: {dict(resp.headers)}")

        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        logger.debug(f"[{task.host.name}] Content-Type: {content_type}")

        content = resp.json() if "json" in content_type else resp.text
        logger.debug(f"[{task.host.name}] Response size: {len(str(content))} chars")

        return Result(host=task.host, result=_pretty_json(content), changed=False)

    except httpx.HTTPStatusError as e:
        logger.error(f"[{task.host.name}] HTTP error {e.response.status_code}: {e.response.text[:200]}")
        return Result(host=task.host, failed=True,
                      result=f"GET {url} -> {e.response.status_code} {e.response.text}")
    except httpx.TimeoutException as e:
        logger.error(f"[{task.host.name}] Request timeout: {e}")
        return Result(host=task.host, failed=True, result=f"GET {url} timed out: {e}")
    except Exception as e:
        logger.error(f"[{task.host.name}] Unexpected error: {type(e).__name__}: {e}")
        logger.exception(f"[{task.host.name}] Full traceback:")
        return Result(host=task.host, failed=True, result=f"GET {url} failed: {e}")


def restconf_put(task: Task, path: str, payload: Dict[str, Any]) -> Result:
    """Execute RESTCONF PUT request"""
    logger.debug(f"[{task.host.name}] Starting RESTCONF PUT for path: {path}")

    try:
        client = _get_client(task)
    except ValueError as e:
        logger.error(f"[{task.host.name}] Failed to get client: {e}")
        return Result(host=task.host, failed=True, result=str(e))

    url = f"/data/{path.strip('/')}"
    logger.debug(f"[{task.host.name}] Full URL: {client.base_url}{url}")
    logger.debug(f"[{task.host.name}] Payload keys: {list(payload.keys())}")
    logger.debug(f"[{task.host.name}] Payload size: {len(json.dumps(payload))} bytes")

    try:
        logger.debug(f"[{task.host.name}] Sending PUT request...")
        resp = client.put(url, json=payload)
        logger.debug(f"[{task.host.name}] Response status: {resp.status_code}")

        resp.raise_for_status()

        body = resp.json() if resp.content else {"status": "ok"}
        logger.debug(f"[{task.host.name}] PUT successful")

        return Result(host=task.host, result=_pretty_json(body), changed=True)

    except httpx.HTTPStatusError as e:
        logger.error(f"[{task.host.name}] HTTP error {e.response.status_code}: {e.response.text[:200]}")
        return Result(host=task.host, failed=True,
                      result=f"PUT {url} -> {e.response.status_code} {e.response.text}")
    except httpx.TimeoutException as e:
        logger.error(f"[{task.host.name}] Request timeout: {e}")
        return Result(host=task.host, failed=True, result=f"PUT {url} timed out: {e}")
    except Exception as e:
        logger.error(f"[{task.host.name}] Unexpected error: {type(e).__name__}: {e}")
        logger.exception(f"[{task.host.name}] Full traceback:")
        return Result(host=task.host, failed=True, result=f"PUT {url} failed: {e}")


def restconf_patch(task: Task, path: str, payload: Dict[str, Any]) -> Result:
    """Execute RESTCONF PATCH request"""
    logger.debug(f"[{task.host.name}] Starting RESTCONF PATCH for path: {path}")

    try:
        client = _get_client(task)
    except ValueError as e:
        logger.error(f"[{task.host.name}] Failed to get client: {e}")
        return Result(host=task.host, failed=True, result=str(e))

    url = f"/data/{path.strip('/')}"
    logger.debug(f"[{task.host.name}] Full URL: {client.base_url}{url}")
    logger.debug(f"[{task.host.name}] Payload keys: {list(payload.keys())}")

    try:
        logger.debug(f"[{task.host.name}] Sending PATCH request...")
        resp = client.patch(url, json=payload)
        logger.debug(f"[{task.host.name}] Response status: {resp.status_code}")

        resp.raise_for_status()

        body = resp.json() if resp.content else {"status": "ok"}
        logger.debug(f"[{task.host.name}] PATCH successful")

        return Result(host=task.host, result=_pretty_json(body), changed=True)

    except httpx.HTTPStatusError as e:
        logger.error(f"[{task.host.name}] HTTP error {e.response.status_code}: {e.response.text[:200]}")
        return Result(host=task.host, failed=True,
                      result=f"PATCH {url} -> {e.response.status_code} {e.response.text}")
    except httpx.TimeoutException as e:
        logger.error(f"[{task.host.name}] Request timeout: {e}")
        return Result(host=task.host, failed=True, result=f"PATCH {url} timed out: {e}")
    except Exception as e:
        logger.error(f"[{task.host.name}] Unexpected error: {type(e).__name__}: {e}")
        logger.exception(f"[{task.host.name}] Full traceback:")
        return Result(host=task.host, failed=True, result=f"PATCH {url} failed: {e}")


def restconf_delete(task: Task, path: str) -> Result:
    """Execute RESTCONF DELETE request"""
    logger.debug(f"[{task.host.name}] Starting RESTCONF DELETE for path: {path}")

    try:
        client = _get_client(task)
    except ValueError as e:
        logger.error(f"[{task.host.name}] Failed to get client: {e}")
        return Result(host=task.host, failed=True, result=str(e))

    url = f"/data/{path.strip('/')}"
    logger.debug(f"[{task.host.name}] Full URL: {client.base_url}{url}")

    try:
        logger.debug(f"[{task.host.name}] Sending DELETE request...")
        resp = client.delete(url)
        logger.debug(f"[{task.host.name}] Response status: {resp.status_code}")

        resp.raise_for_status()
        logger.debug(f"[{task.host.name}] DELETE successful")

        return Result(host=task.host, result="deleted", changed=True)

    except httpx.HTTPStatusError as e:
        logger.error(f"[{task.host.name}] HTTP error {e.response.status_code}: {e.response.text[:200]}")
        return Result(host=task.host, failed=True,
                      result=f"DELETE {url} -> {e.response.status_code} {e.response.text}")
    except httpx.TimeoutException as e:
        logger.error(f"[{task.host.name}] Request timeout: {e}")
        return Result(host=task.host, failed=True, result=f"DELETE {url} timed out: {e}")
    except Exception as e:
        logger.error(f"[{task.host.name}] Unexpected error: {type(e).__name__}: {e}")
        logger.exception(f"[{task.host.name}] Full traceback:")
        return Result(host=task.host, failed=True, result=f"DELETE {url} failed: {e}")


def restconf_close(task: Task) -> Result:
    """Idempotent: safe to call even if client never existed or already closed."""
    logger.debug(f"[{task.host.name}] Attempting to close RESTCONF client")

    store = _get_store(task)
    client = store.get("client")

    if client is None:
        logger.debug(f"[{task.host.name}] No client to close (never created)")
        return Result(host=task.host, result="no client", changed=False)

    try:
        logger.debug(f"[{task.host.name}] Closing httpx.Client")
        client.close()
        logger.debug(f"[{task.host.name}] Client closed successfully")
    except Exception as e:
        logger.warning(f"[{task.host.name}] Error during client close: {e}")
    finally:
        # Remove the reference from host.data
        store.pop("client", None)
        logger.debug(f"[{task.host.name}] Client reference removed from store")

    return Result(host=task.host, result="closed", changed=False)