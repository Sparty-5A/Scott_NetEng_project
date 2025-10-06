import re
from nornir.core.task import Task, Result
from nornir_netmiko.tasks import netmiko_send_command

def show_router_interface(task: Task, cmd: str = "show router interface") -> Result:
    # Normalize to classic CLI and disable pager
    task.run(netmiko_send_command, command_string="classic-cli", expect_string=r"A:.*#", cmd_verify=False)
    task.run(netmiko_send_command, command_string="environment no more", expect_string=r"#", cmd_verify=False)
    r = task.run(netmiko_send_command, command_string=cmd, expect_string=r"#", cmd_verify=False, read_timeout=90)

    # Simple error scan
    for pat in (r"Error:", r"Invalid parameter", r"Invalid syntax", r"Command not found"):
        if re.search(pat, r.result):
            return Result(host=task.host, result=f"FAILED ({pat}):\n{r.result}", failed=True, changed=False, name=cmd)
    return Result(host=task.host, result=r.result, changed=False, name=cmd)
