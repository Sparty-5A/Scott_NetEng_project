# import sys
# sys.path.insert(0, '/home/sparty/Scott_NetEng_project')

import argparse
from nornir import InitNornir
from nornir.core.filter import F
from net.nornir.tasks.show_httpx import restconf_get, restconf_close
from automation.lib.logging_setup import setup_logging

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True, help="inventory name or hostname")
    p.add_argument("--path", required=True, help="RESTCONF data path, e.g. 'openconfig-interfaces:interfaces/interface'")
    args = p.parse_args()

    logger, console = setup_logging()

    # Log script invocation details
    logger.debug(f"Script started with args: host={args.host}, path={args.path}")

    # Initialize Nornir
    logger.debug("Initializing Nornir with config.yaml")
    nr = InitNornir(config_file="config.yaml", logging={"enabled": False})
    logger.debug(f"Nornir initialized with {len(nr.inventory.hosts)} total hosts")

    # Filter hosts
    logger.debug(f"Filtering by name: {args.host}")
    flt = nr.filter(F(name=args.host))
    if not flt.inventory.hosts:
        logger.debug(f"No match by name, trying hostname: {args.host}")
        flt = nr.filter(F(hostname=args.host))

    if not flt.inventory.hosts:
        logger.error(f"Host filter failed: no match for '{args.host}'")
        console.error(f"No hosts matched filter: {args.host}")
        return 2

    matched_hosts = list(flt.inventory.hosts.keys())
    logger.debug(f"Filter matched {len(matched_hosts)} host(s): {matched_hosts}")

    console.info(f"RESTCONF GET on: {matched_hosts} path={args.path}")

    # Run the task
    logger.debug(f"Executing restconf_get task on {len(matched_hosts)} host(s)")
    res = flt.run(task=restconf_get, path=args.path)
    logger.debug(f"Task completed for {len(res)} host(s)")

    # Process results
    for h, multi in res.items():
        logger.debug(f"Processing results for host: {h} ({len(multi)} result(s))")
        for idx, r in enumerate(multi):
            status = "FAILED" if r.failed else "OK"
            logger.debug(f"[{h}] Result {idx}: status={status}, changed={r.changed}")
            console.info(f"[{h}] {status}")
            if r.result:
                console.info(r.result)
                logger.debug(f"[{h}] Result length: {len(str(r.result))} chars")
            if r.failed and r.exception:
                logger.debug(f"[{h}] Exception details: {r.exception}")

    # Cleanup
    logger.debug("Closing RESTCONF clients")
    flt.run(task=restconf_close)
    logger.debug("Script completed successfully")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())