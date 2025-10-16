import sys

sys.path.insert(0, "/")
import argparse

from automation.lib.logging_setup import setup_logging
from net.nornir.tasks.show_httpx_bk import restconf_close, restconf_get
from nornir import InitNornir
from nornir.core.filter import F


def main():

    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True, help="inventory name or hostname")
    p.add_argument(
        "--path", required=True, help="RESTCONF data path, e.g. 'ietf-interfaces:interfaces'"
    )
    args = p.parse_args()

    logger, console = setup_logging()

    nr = InitNornir(config_file="config.yaml", logging={"enabled": False})

    flt = nr.filter(F(name=args.host))
    if not flt.inventory.hosts:
        flt = nr.filter(F(hostname=args.host))
    if not flt.inventory.hosts:
        console.error(f"No hosts matched filter: {args.host}")
        return 2

    console.info(f"RESTCONF GET on: {list(flt.inventory.hosts.keys())} path={args.path}")
    res = flt.run(task=restconf_get, path=args.path)

    for h, multi in res.items():
        for r in multi:
            status = "FAILED" if r.failed else "OK"
            console.info(f"[{h}] {status}")
            if r.result:
                console.info(r.result)
    # optional: close clients
    flt.run(task=restconf_close)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
