# SensiWatch

**SensiWatch** is a high-performance, hardened remote monitoring platform engineered for unattended server farms, industrial kiosks, and controlled examination environments. It provides secure, real-time visual oversight of multiple target nodes via a Zero-Trust architecture.


## Architectural Vision

SensiWatch replaces traditional, insecure remote monitoring protocols with cryptographic identity verification and adaptive media streaming.

* **Zero-Trust Security:** mTLS-only communication backbone. Every client agent is cryptographically verified by an embedded Certificate Authority (CA).
* **Intelligent Streaming:** A dual-tier pipeline that optimizes for network health.
* *Thumbnail Mode:* Adaptive, low-framerate keyframes for grid-view monitoring.
* *Focus Mode:* Hardware-accelerated, low-latency WebRTC streaming upon administrator demand.


* **Modern Stack:** Built on Python 3.13+ for high-throughput concurrency, FastAPI for secure signaling, and Tailwind v4 for a clean administrative interface.
* **Infrastructure Resilience:** Split-tunnel telemetry ensures that diagnostic logs reach the development team even during catastrophic local network partitions.

## Tech Stack

* **Core:** Python 3.13+, FastAPI, uv (Workspaces)
* **Database:** SQLite (Embedded)
* **Security:** mTLS (Mutual TLS), Embedded CA, OS-level ACL hardening
* **Frontend:** Tailwind v4, Lucide Icons, JS Toastify
* **Streaming:** WebRTC (aiortc) & WebSocket Signaling

## MVP Roadmap

The system is developed through a strictly gated milestone process:

1. **Foundation:** mTLS Handshake & Embedded CA Enrollment.
2. **Infrastructure:** Headless Daemon Lifecycle & Presence Telemetry.
3. **Visibility:** Thumbnail Pipeline & Adaptive Grid UI.
4. **Reliability:** Fault-Tolerant Out-of-Band Telemetry.
5. **Deployment:** Silent Binary Packaging & Containerized Hosting.

## Getting Started

### Prerequisites

* Python 3.13+
* uv package manager

### Installation

1. **Clone the Repository:**
```bash
git clone https://github.com/SteveSplash934/SensiWatch.git
cd SensiWatch
```

2. **Sync Workspace:**
```bash
uv venv --system-site-packages
uv sync
```

### Deployment

Detailed deployment instructions for containerized server hosting and silent headless client installation are provided in the `/deploy` directory.

## Security Policy

SensiWatch utilizes mTLS and OS-level access control lists to ensure that private keys remain inaccessible to local system users. Refer to the project documentation for cryptographic implementation details.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).