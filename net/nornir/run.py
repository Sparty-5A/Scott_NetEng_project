import argparse
from nornir import InitNornir
from nornir.core.filter import F
from nornir_utils.plugins.functions import print_result
from automation.lib.logging_setup import setup_logging
from net.nornir.tasks.show import show_router_interface

def main():
    parser = argparse.ArgumentParser(description="Run Nornir show command")
    parser.add_argument("--host", required=True, help="Host filter: inventory name or hostname")
    parser.add_argument("--cmd", default="show ip interface brief")
    args = parser.parse_args()

    logger, console = setup_logging()

    nr = InitNornir(config_file="net/nornir/config.yaml", logging={"enabled": False})

    # Try filter by name first, otherwise by hostname
    filtered = nr.filter(F(name=args.host))
    if not filtered.inventory.hosts:
        filtered = nr.filter(F(hostname=args.host))

    if not filtered.inventory.hosts:
        console.error(f"No hosts matched filter: {args.host}")
        return 2

    console.info(f"Running on: {list(filtered.inventory.hosts.keys())}")
    result = filtered.run(task=show_router_interface, cmd=args.cmd)

    # Print user-facing summary to console
    for h, multi in result.items():
        for r in multi:
            status = "FAILED" if r.failed else "OK"
            console.info(f"[{h}] {r.name}: {status}")
            if r.result:
                console.info(r.result)

    # Also print full Nornir result tree to console if desired:
    print_result(result)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
