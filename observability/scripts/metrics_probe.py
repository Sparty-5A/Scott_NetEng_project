import time, subprocess, sys
from loguru import logger

def ping(host: str, count: int = 3) -> float | None:
    try:
        out = subprocess.check_output(["ping", "-c", str(count), host], text=True)
        # naive parse
        for line in out.splitlines():
            if "avg" in line or "rtt min/avg/max" in line:
                parts = line.split("=")[-1].split("/")
                return float(parts[1])
    except Exception as e:
        logger.error(f"ping failed: {e}")
    return None

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "8.8.8.8"
    while True:
        rtt = ping(host) or -1.0
        logger.info(f"{host} avg_rtt_ms={rtt}")
        time.sleep(30)
