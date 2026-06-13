# PRODUCT REQUIREMENTS DOCUMENT

## 1. Product Overview & Objectives

SensiWatch Enterprise is a lightweight, secure, continuous screen-monitoring platform designed specifically for unattended infrastructure (server farms, digital kiosks) and controlled instructional environments (examination centers). The primary objective is to enable a single administrator to maintain real-time visual oversight of multiple target screens concurrently over a local network without requiring manual user intervention, per-session consent prompts, or heavy system overhead.

---

## 2. Target Use Cases & Personas

* **Infrastructure Administrators (Server Farms/Kiosks):** Requires continuous, low-overhead monitoring of headless or automated systems to track runtime conditions, detect visual freezes, or verify interface state changes.
* **Examination Proctors / Janitors (Educational Centers):** Requires an automated, responsive matrix of student displays to detect unauthorized actions or exam malpractice from a single viewing station.

---

## 3. Functional Requirements

### 3.1 Unattended Client Execution (The Agent)

* **Headless Operation:** The client must execute completely in the background as an OS system service (Windows Service / Linux Systemd) with zero graphical user interface or system tray presence on the monitored machine.
* **Boot-Time Activation:** The agent must initialize and attempt connectivity immediately upon operating system boot, prior to user login.
* **Autonomous Lifecycle Management:** The client must gracefully handle network drops, parent server restarts, or system power states via a silent back-off and auto-reconnection loop without throwing blocking OS pop-ups.

### 3.2 Central Monitoring Space (The Server Dashboard)

* **Adaptive Video Matrix:** The primary administrative panel must render a responsive grid constrained to a clean layout (nominally a 4x2 or 5x2 aspect ratio matrix) to prevent human cognitive fatigue and browser rendering failure.
* **Paginated Viewports:** When the number of monitored nodes exceeds the active grid dimensions, the dashboard must implement clean pagination or viewport-based loading to control active network streams.
* **Dual-Tier Streaming Mechanics:**
* **Thumbnail Mode (Default):** Monitored nodes visible in the active grid page but not actively expanded must transmit highly compressed, low-framerate keyframes to conserve network bandwidth and host CPU.
* **Focus Mode (On-Demand):** Clicking an individual node grid item must seamlessly scale the layout into a full-screen, high-resolution, low-latency video stream. Closing the focused view immediately downgrades the stream back to Thumbnail Mode.



### 3.3 Out-of-Band Telemetry & Error Redirection

* **Primary Ingestion:** Under nominal conditions, client system metrics (CPU utilization, memory usage, network state) and application alerts must stream directly to the parent server's diagnostic database.
* **Fail-Safe Developer Redirection:** If a client experiences a fatal application failure, or cannot establish contact with its local parent server, it must alter its network routing table to push diagnostic payloads and tracebacks to an external, 24/7-operational Developer Telemetry Hook.

---

## 4. Non-Functional Requirements

### 4.1 Security, Trust & Data Privacy

* **Zero-Trust Identity Verification:** The platform must reject standard text-based passphrases or static pre-shared keys (PSKs). Communication boundaries must be cryptographically enforced via Mutual TLS (mTLS).
* **Local Secret Hardening:** Cryptographic keys, certificates, and configuration variables deployed on the client host must be protected via strict operating system Access Control Lists (ACLs) to mitigate local extraction risks.

### 4.2 Performance & Resource Minimization

* **Client Footprint:** Memory utilization of the background daemon must remain minimal. Frame processing must leverage local hardware video encoders to eliminate CPU execution spikes.
* **Server Concurrency:** The backend engine must handle multiple simultaneous incoming client handshakes and video feeds asynchronously without deadlocks.
* **Zero External Footprint:** The server space must utilize an embedded, file-based database architecture to eliminate the operational complexity of deploying external database clusters.

---

## 5. User Interface & Experience (UX) Specifications

* **Design Paradigm:** Modern, dark-mode-first administrative interface emphasizing ultra-clean layouts, data density, and immediate scannability.
* **Typography & Semantics:** Distinct layout hierarchy utilizing stylized geometric sans-serif typefaces for structural headers and highly readable, geometric neo-grotesque fonts for body elements, tabular data, and device labels.
* **Interactivity Alerts:** Stream initialization errors, client disconnections, or telemetry exceptions must trigger asynchronous, non-blocking toast notifications that automatically dismiss without disrupting active video observation.

---