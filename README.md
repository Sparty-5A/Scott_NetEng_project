# NetEng Portfolio

A ready-to-fork project that demonstrates **NetDevOps**, **Cloud networking**, and **Validation/Observability** patterns.
Designed for daily use and to showcase projects in interviews quickly.

## Highlights
- Python + Loguru logging with **file DEBUG** and **console user-output** split.
- Nornir 3.x with Netmiko 4.x tasks; strict, deterministic CLI session handling.
- Terraform AWS VPC scaffold (optional).
- Pre-commit hooks (ruff, black), basic CI (lint + tests).
- Slots for Batfish/pyATS and telemetry dashboards.

## Quick start

```bash
# 1) Create a virtual environment
python -m venv .venv && . .venv/bin/activate     # (Windows: .venv\Scripts\activate)

# 2) Install deps
pip install -r requirements.txt

# 3) (Optional) Configure inventory for your devices in net/nornir/inventory/hosts.yaml

# 4) Run a sample Nornir task (shows console output; DEBUG to logs/)
python net/nornir/run_ssh.py --host 192.0.2.10 --cmd "show router interface"
```

> By default, **DEBUG** logs go to `logs/nornir_debug.log` while **console** shows only user-facing lines.

## Repo layout
```
infra/terraform/      # AWS VPC scaffold (optional)
net/nornir/           # Nornir inventory + tasks + runner
automation/lib/       # shared Python libs (logging, utils)
observability/        # telemetry + dashboards (placeholders)
validation/           # pyATS/Batfish scaffolding
.github/workflows/    # CI pipeline (lint + tests)
```

## Notes
- CI avoids contacting real devices; network tests are marked to skip by default.
- Replace placeholders with your actual org tooling (e.g., TGW, SD-WAN controllers, etc.).
