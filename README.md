# Network Engineering & Automation Portfolio

> **Scott's NetDevOps Portfolio** - Demonstrating network automation, orchestration, cloud networking, and validation skills

[![CI Status](https://github.com/Sparty-5A/Scott_NetEng_project/workflows/ci/badge.svg)](https://github.com/Sparty-5A/Scott_NetEng_project/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Portfolio Overview

This repository demonstrates production-ready network automation and orchestration skills across multiple domains:

- **Network Orchestration** with Cisco NSO (RESTCONF API)
- **Device Automation** with Python (httpx, Scrapli)
- **Infrastructure as Code** with pytest and validation
- **CI/CD Integration** with GitHub Actions
- **Cloud Networking** (AWS - planned)
- **SD-WAN/Overlay Design** (planned)

**Background:** CCNP Routing & Switching, DevNet Associate, Python/NETCONF/RESTCONF/gNMI experience

---

## 📚 Project Structure

```
Scott_NetEng_project/
├── cisco_8000v_basics/          # Direct device automation
│   ├── automation/              # Scrapli helpers, safe getters
│   ├── net/nornir/             # Nornir tasks (RESTCONF, SSH)
│   └── tests/                  # Integration tests
│
├── nso_orchestration/          # NSO orchestration
│   ├── automation/
│   │   └── nso_client.py       # NSO RESTCONF client
│   ├── examples/
│   │   └── sync_devices.py     # Device sync automation
│   └── tests/
│       └── test_nso_loopback.py # Loopback provisioning tests
│
├── .github/workflows/          # CI/CD pipeline
├── pyproject.toml             # Project config & dependencies
└── README.md                  # This file
```

---

## ✅ Completed Work

### Task 1: NSO Orchestration & Device Automation

#### 🔧 **Cisco NSO RESTCONF Client**
- **Full RESTCONF API wrapper** with httpx
- **Safe getter pattern** with comprehensive error handling
- **XML payload support** for NSO-specific operations
- **Transactional operations**: sync, configure, rollback
- **Dry-run mode** for pre-validation

**Key Features:**
```python
# Create NSO client
client = NSOClient(host="10.10.20.49")

# Sync devices from network
client.sync_from_device("dist-rtr01")

# Configure with dry-run
dry_result = client.configure_loopback(
    device_name="dist-rtr01",
    loopback_id="100",
    ip_address="10.100.100.1",
    netmask="255.255.255.255",
    dry_run=True  # Preview changes
)

# Apply configuration
client.configure_loopback(..., dry_run=False)

# Rollback if needed
client.rollback(0)  # Undo last change
```

#### 🧪 **Comprehensive Test Suite**

**Test Coverage:**
- ✅ NSO connectivity and health checks
- ✅ Device sync operations
- ✅ Loopback interface creation with validation
- ✅ Multiple loopback batch operations
- ✅ Dry-run pre-validation
- ✅ Automated rollback on failure
- ✅ Interface deletion and cleanup

**Test Results:** 5/5 passing (integration tests)

```bash
# Run NSO tests (requires VPN to DevNet sandbox)
uv run pytest nso_orchestration/tests -v

PASSED test_nso_health_check
PASSED test_devices_discovered
PASSED test_device_sync
PASSED test_create_loopback
PASSED test_create_multiple_loopbacks
PASSED test_dry_run_loopback
PASSED test_rollback_loopback
PASSED test_delete_loopback
```

#### 📊 **Device Sync Automation**

Automated device synchronization script:
```bash
uv run python nso_orchestration/examples/sync_devices.py

# Output:
# Found 9 devices to sync
# Syncing core-rtr01... ✓
# Syncing dev-dist-rtr01... ✓
# ...
# Sync complete: 9 succeeded, 0 failed
```
## Deletion Policy

The intent engine supports two modes for handling loopbacks that exist on devices but are not declared in the intent file:

### Safe Mode (Default) ✅ Recommended
```yaml
devices:
  - name: router1
    delete_unmanaged_loopbacks: false  # or omit (defaults to false)
    loopbacks:
      - id: 100
        ipv4: 10.100.100.1
        netmask: 255.255.255.255
```

**Behavior:** Only manages loopbacks explicitly declared in intent. Existing loopbacks not in the intent file are **ignored** (not deleted).

**Use when:**
- ✅ Gradually adopting intent-based management
- ✅ Multiple teams/tools manage different loopbacks
- ✅ You want maximum safety against accidental deletion

### Strict Mode ⚠️ Use with Caution
```yaml
devices:
  - name: router1
    delete_unmanaged_loopbacks: true
    loopbacks:
      - id: 100
        ipv4: 10.100.100.1
        netmask: 255.255.255.255
```

**Behavior:** Intent file is the single source of truth. Loopbacks not in the intent file are **deleted**.

**Use when:**
- ✅ Fresh device configuration
- ✅ Lab/test environments
- ✅ You want strict enforcement of intent
- ⚠️ **Only if you're certain the intent file is complete!**

### Mixed Mode

Different devices can have different policies:
```yaml
devices:
  - name: prod-router
    delete_unmanaged_loopbacks: false  # Safe for production
    loopbacks: [...]
  
  - name: lab-router
    delete_unmanaged_loopbacks: true   # Strict for lab
    loopbacks: [...]
```
---

## 🚧 Planned Work

### Task 2: AWS Cloud Networking (In Progress)
**Skills:** Terraform, AWS VPC, Site-to-Site VPN, hybrid cloud

**Planned Deliverables:**
- Terraform-managed VPC with multi-AZ design
- IPSec/BGP Site-to-Site VPN to on-prem lab
- Transit Gateway integration
- Automated provisioning: Terraform + NSO orchestration
- VPC Flow Logs analysis for troubleshooting

---

### Task 3: SD-WAN / Overlay Design
**Skills:** Application-aware routing, policy-based forwarding, telemetry

**Planned Deliverables:**
- DIY overlay with WireGuard + FRR BGP
- Application-aware path selection based on latency/jitter
- Policy-driven traffic steering
- Latency/loss monitoring with Grafana
- Failover testing and validation

---

### Task 4: Observability & Intent Validation
**Skills:** Streaming telemetry, gNMI, SLOs, SRE practices

**Planned Deliverables:**
- gNMI telemetry → InfluxDB → Grafana dashboards
- Batfish or pyATS intent validation ("no duplicate subnets", "exact BGP adjacencies")
- Full CI/CD pipeline: lint → test → validate → deploy → verify
- SRE-style incident postmortem template
- SLO dashboards with alerting

---

## 🛠️ Setup & Installation

### Prerequisites
- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **DevNet Sandbox Access** (for integration tests)
  - Free registration at [DevNet Sandbox](https://devnetsandbox.cisco.com/)
  - VPN client (Cisco AnyConnect)

### Quick Start

```bash
# Clone repository
git clone https://github.com/Sparty-5A/Scott_NetEng_project
cd Scott_NetEng_project

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### Running Tests

```bash
# Run all unit tests (no sandbox required)
uv run pytest -m "not integration" -v

# Run all tests including integration (requires VPN + sandbox)
uv run pytest -v

# Run specific module tests
uv run pytest nso_orchestration/tests -v
uv run pytest cisco_8000v_basics/tests -v

# Run with coverage
uv run pytest --cov --cov-report=html
```

### Setting Up DevNet Sandbox Access

1. **Reserve NSO Sandbox**
   - Go to [DevNet Sandbox](https://devnetsandbox.cisco.com/)
   - Search for "NSO Reservable"
   - Reserve sandbox (7 days, extendable)

2. **Configure Environment Variables**

Each module has an `.env.example` file:

```bash
# NSO module
cd nso_orchestration
cp .env.example .env
# Edit .env with your sandbox credentials

# Cisco 8000v module
cd cisco_8000v_basics
cp .env.example .env
# Edit .env with your sandbox credentials
```

Example `.env`:
```bash
NSO_HOST=10.10.20.49
NSO_PORT=8080
NSO_USERNAME=developer
NSO_PASSWORD=C1sco12345
```

3. **Connect to VPN**
   - Use Cisco AnyConnect with credentials from sandbox email
   - Verify connectivity: `ping 10.10.20.49`

4. **Sync Devices** (NSO only)
```bash
uv run python nso_orchestration/examples/sync_devices.py
```

---

## 📈 Skills Demonstrated

### Technical Skills

| Skill | Evidence | Status |
|-------|----------|--------|
| **Python Automation** | httpx client, safe getters, error handling | ✅ Complete |
| **NSO/RESTCONF** | Full API wrapper, XML/JSON payloads | ✅ Complete |
| **Pre/Post Validation** | pytest test suite with checks | ✅ Complete |
| **Dry-Run Validation** | NSO dry-run mode integration | ✅ Complete |
| **Automated Rollback** | Rollback tracking and execution | ✅ Complete |
| **CI/CD** | GitHub Actions with lint/test | ✅ Complete |
| **Terraform/IaC** | AWS VPC automation | 🚧 Planned |
| **Cloud Networking** | AWS hybrid connectivity | 🚧 Planned |
| **SD-WAN Concepts** | Overlay design, app-aware routing | 🚧 Planned |
| **Streaming Telemetry** | gNMI, Grafana dashboards | 🚧 Planned |

### Soft Skills

- **Problem Solving**: Debugged NSO RESTCONF API differences (XML vs JSON)
- **Documentation**: Comprehensive code comments and README
- **Testing**: Test-driven development with pytest
- **Version Control**: Git workflow with meaningful commits
- **DevOps Mindset**: Automated validation and rollback for safety

---

## 🎓 Certifications

- ✅ **CCNP Enterprise**
- ✅ **DevNet Associate**
- 🚧 **AWS Advanced Networking - Specialty** (planned)
- 🚧 **Terraform Associate** (planned)

---

## 📸 Portfolio Evidence

### CI/CD Pipeline
![CI Pipeline](docs/screenshots/ci-pipeline.png)

### NSO Loopback Provisioning
![Loopback Test](docs/screenshots/nso-loopback-test.png)

### Dry-Run Validation
![Dry Run](docs/screenshots/nso-dry-run.png)

### Rollback Demonstration
![Rollback](docs/screenshots/nso-rollback.png)

---

## 🔗 Additional Resources

- **NSO Documentation**: https://developer.cisco.com/docs/nso/
- **DevNet Sandboxes**: https://devnetsandbox.cisco.com/
- **RESTCONF RFC**: https://datatracker.ietf.org/doc/html/rfc8040
- **YANG Models**: https://github.com/YangModels/yang

---

## 📧 Contact

**Scott Penry**  
📧 Email: scottpenry@comcast.net  
🔗 LinkedIn: [linkedin.com/in/scott-penry-0a277829/](https://linkedin.com/in/scott-penry-0a277829/)  
💼 GitHub: [github.com/Sparty-5A](https://github.com/Sparty-5A)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

- Cisco DevNet for sandbox access
- NSO documentation and community
- Open source Python networking libraries (httpx, pytest, loguru)