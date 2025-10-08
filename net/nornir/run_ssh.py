from nornir import InitNornir
from nornir.core.filter import F
from nornir_utils.plugins.functions import print_result
from automation.lib.logging_setup import setup_logging
from net.nornir.tasks.show_ssh import show_router_interface

def main():

    logger, console = setup_logging()

    nr = InitNornir(config_file="config.yaml", logging={"enabled": False})

    result = nr.run(task=show_router_interface)

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
