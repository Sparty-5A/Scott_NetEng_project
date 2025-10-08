import json
import httpx
from typing import Any, Dict, Optional
from nornir.core.task import Task, Result

HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}

def _get_client(task: Task) -> httpx.Client:
    """
    Cache a per-host httpx.Client for connection pooling.
    """
    key = "_restconf_httpx_client"
    client = task.host.get(key)
    if client:
        return client

    rc: Dict[str, Any] = task.host.get("restconf") or task.host.data.get("restconf", {})
    base = rc.get("base_url")
    user = rc.get("username")
    pwd  = rc.get("password")
    verify = rc.get("verify_ssl", True)

    if not base or not user or not pwd:
        raise ValueError("Missing restconf.base_url/username/password in host data")

    client = httpx.Client(
        base_url=base.rstrip("/"),
        auth=(user, pwd),
        headers=HEADERS,
        verify=verify
    )
    # cache it for this host
    task.host[key] = client
    return client

def _pretty_json(body: Any) -> str:
    try:
        return json.dumps(body, indent=2)
    except Exception:
        return str(body)

def restconf_get(task: Task, path: str) -> Result:
    client = _get_client(task)
    url = f"/data/{path.strip('/')}"
    try:
        resp = client.get(url)
        resp.raise_for_status()
        content = resp.json() if "json" in resp.headers.get("content-type", "") else resp.text
        return Result(host=task.host, result=_pretty_json(content), changed=False)
    except httpx.HTTPStatusError as e:
        return Result(host=task.host, failed=True,
                      result=f"GET {url} -> {e.response.status_code} {e.response.text}")
    except Exception as e:
        return Result(host=task.host, failed=True, result=f"GET {url} failed: {e}")

def restconf_put(task: Task, path: str, payload: Dict[str, Any]) -> Result:
    client = _get_client(task)
    url = f"/data/{path.strip('/')}"
    try:
        resp = client.put(url, json=payload)
        resp.raise_for_status()
        body = resp.json() if resp.content else {"status": "ok"}
        return Result(host=task.host, result=_pretty_json(body), changed=True)
    except httpx.HTTPStatusError as e:
        return Result(host=task.host, failed=True,
                      result=f"PUT {url} -> {e.response.status_code} {e.response.text}")
    except Exception as e:
        return Result(host=task.host, failed=True, result=f"PUT {url} failed: {e}")

def restconf_patch(task: Task, path: str, payload: Dict[str, Any]) -> Result:
    client = _get_client(task)
    url = f"/data/{path.strip('/')}"
    try:
        resp = client.patch(url, json=payload)
        resp.raise_for_status()
        body = resp.json() if resp.content else {"status": "ok"}
        return Result(host=task.host, result=_pretty_json(body), changed=True)
    except httpx.HTTPStatusError as e:
        return Result(host=task.host, failed=True,
                      result=f"PATCH {url} -> {e.response.status_code} {e.response.text}")
    except Exception as e:
        return Result(host=task.host, failed=True, result=f"PATCH {url} failed: {e}")

def restconf_delete(task: Task, path: str) -> Result:
    client = _get_client(task)
    url = f"/data/{path.strip('/')}"
    try:
        resp = client.delete(url)
        resp.raise_for_status()
        return Result(host=task.host, result="deleted", changed=True)
    except httpx.HTTPStatusError as e:
        return Result(host=task.host, failed=True,
                      result=f"DELETE {url} -> {e.response.status_code} {e.response.text}")
    except Exception as e:
        return Result(host=task.host, failed=True, result=f"DELETE {url} failed: {e}")
