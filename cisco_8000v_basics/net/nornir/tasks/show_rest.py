import json

import requests
from nornir.core.task import Result, Task

HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}


def restconf_get(task: Task, path: str) -> Result:
    rc = task.host.get("restconf", None) or task.host.data.get("restconf", {})
    base = rc.get("base_url")
    user = rc.get("username")
    pwd = rc.get("password")
    verify = rc.get("verify_ssl", True)
    if not base or not user or not pwd:
        return Result(
            host=task.host,
            failed=True,
            result="Missing restconf config (base_url/username/password)",
        )

    url = f"{base}/data/{path.strip('/')}"
    resp = requests.get(url, headers=HEADERS, auth=(user, pwd), verify=verify, timeout=30)
    if not resp.ok:
        return Result(
            host=task.host, failed=True, result=f"GET {url} -> {resp.status_code} {resp.text}"
        )

    # pretty JSON string for console, raw data in result
    try:
        payload = resp.json()
        pretty = json.dumps(payload, indent=2)
    except Exception:
        payload, pretty = resp.text, resp.text

    return Result(host=task.host, result=pretty, changed=False)
