# SensiWatch MVP Execution Roadmap

## Objective

This document serves as the mandatory execution sequence for the SensiWatch Enterprise build. The LLM must follow this order strictly, ensuring each milestone is verified before proceeding to the next.

## Milestone 1: Security & Enrollment (Foundation)

* **1.1 Workspace Init:** Standardize `uv` workspace and modular directory structure.
* **1.2 Embedded CA Engine:** Implement an internal CA module within the server to generate and sign client certificates.
* **1.3 Bootstrap Enrollment:** Build the `/api/v1/enroll` endpoint. Implement a one-time token mechanism and secure CSR-to-Certificate signing flow.
* **1.4 Client Hardening:** Implement the client-side secret storage module, including OS-level ACLs (chmod 600 / System-only access) for private keys.
* **Validation Gate:** Verify that a client can request an identity, receive a signed certificate, and authenticate successfully via mTLS to a dummy FastAPI endpoint.

## Milestone 2: Connectivity & Presence (Infrastructure)

* **2.1 WebSocket Signaling:** Implement the persistent, mTLS-secured WebSocket connection.
* **2.2 Daemon Lifecycle:** Build the client as a headless service; implement silent auto-reconnection and state-machine logic.
* **2.3 Heartbeat Telemetry:** Implement the baseline status tracking (Online/Offline) in SQLite.
* **Validation Gate:** Verify the server dashboard correctly tracks the connection/disconnection of client nodes.

## Milestone 3: The Media Pipeline (Visibility)

* **3.1 Thumbnail Engine:** Implement Tier-1 streaming (compressed, low-framerate keyframes) over the WebSocket signaling channel.
* **3.2 Admin UI Grid:** Build the Tailwind v4 responsive grid (4x2 / 5x2) with paginated viewport management.
* **3.3 WebRTC Signaling:** Implement the `START_WEBRTC` / `STOP_WEBRTC` protocol negotiation.
* **Validation Gate:** Verify the server renders active low-res thumbnails and can successfully escalate to a high-resolution feed upon focus.

## Milestone 4: Resilience & Diagnostics (Reliability)

* **4.1 Split-Tunnel Telemetry:** Implement the telemetry logic that routes logs to the parent server, with fallback to the developer hook.
* **4.2 Error Handling:** Implement global exception catching in the client daemon to trigger the secondary telemetry route.
* **Validation Gate:** Simulate a server network partition; verify the client correctly redirects diagnostics to the external developer hook.

## Milestone 5: Deployment Hardening (Shipment)

* **5.1 Installer Bundling:** Package the client into a silent-install binary using PyInstaller.
* **5.2 Dockerization:** Finalize the server `docker-compose` setup with SQLite persistent storage.
* **Final Validation:** Full end-to-end demonstration of a fresh installation, bootstrap enrollment, and active monitoring.

---