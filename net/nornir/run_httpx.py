import sys
sys.path.insert(0,'/home/sparty/Scott_NetEng_project')
import argparse
from nornir import InitNornir
from nornir.core.filter import F
from loguru import logger
from net.nornir.tasks.show_httpx import restconf_get

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True, help="inventory name or hostname")
    p.add_argument("--path", required=True, help="RESTCONF data path, e.g. 'ietf-interfaces:interfaces'")
    args = p.parse_args()

    # logger, console = setup_logging()

    nr = InitNornir(config_file="config.yaml", logging={"enabled": False})

    flt = nr.filter(F(name=args.host))
    if not flt.inventory.hosts:
        flt = nr.filter(F(hostname=args.host))
    if not flt.inventory.hosts:
        logger.error(f"No hosts matched filter: {args.host}")
        return 2

    logger.info(f"RESTCONF GET on: {list(flt.inventory.hosts.keys())} path={args.path}")
    res = flt.run(task=restconf_get, path=args.path)

    for h, multi in res.items():
        for r in multi:
            status = "FAILED" if r.failed else "OK"
            logger.info(f"[{h}] {status}")
            if r.result:
                logger.info(r.result)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
