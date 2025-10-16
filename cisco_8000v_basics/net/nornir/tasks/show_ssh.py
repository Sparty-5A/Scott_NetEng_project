import re

from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command


def show_router_interface(task: Task, cmd: str = "show ip interface brief") -> Result:
    # Normalize to classic CLI and disable pager
    r = task.run(netmiko_send_command, command_string=cmd)

    # Simple error scan
    for pat in (r"Error:", r"Invalid parameter", r"Invalid syntax", r"Command not found"):
        if re.search(pat, r.result):
            return Result(
                host=task.host,
                result=f"FAILED ({pat}):\n{r.result}",
                failed=True,
                changed=False,
                name=cmd,
            )
    return Result(host=task.host, result=r.result, changed=False, name=cmd)
