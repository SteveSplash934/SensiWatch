
# PROJECT ENGINEERING DOCUMENT

## 1. System Architecture & Tech Stack

The engineering architecture is built as a highly decoupled, asynchronous monorepo optimized for Python 3.13+ execution and deterministic dependency management.

```
+---------------------------------------------------------------------------------------+
|                                  MONOREPO WORKSPACE                                   |
|                                (uv Workspace Manager)                                 |
+---------------------------------------------------------------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v                                             v
+---------------------------------------+     +---------------------------------------+
|            /server SPACE              |     |             /client SPACE             |
|  - FastAPI (Python 3.13+ Async)       |     |  - Python 3.13+ Headless Daemon       |
|  - SQLite (Embedded Data Layer)       |     |  - PyInstaller Native Binary Compiler |
|  - Custom Embedded CA Engine          |     |  - Hardware Accelerated Video Pipeline|
|  - Tailwind v4 / JS / WebSockets      |     |  - Dual-Route Telemetry Client        |
+---------------------------------------+     +---------------------------------------+

```

### 1.1 Server Core Stack

* **Runtime Environment:** Python 3.13+ utilizing native async/await features for high-throughput concurrency.
* **Application Framework:** FastAPI integrated with an ASGI web server layer configured for low-level TLS socket manipulation.
* **Database Engine:** SQLite accessed via an asynchronous Data Access Layer (DAL) to handle configuration metadata, cryptographic state, and active client nodes.
* **Frontend Composition:** Tailwind v4 utility compilation engine, native JavaScript WebRTC/WebSocket wrappers, Lucide SVG icon packs, and Toastify asynchronous notification layers.

### 1.2 Client Core Stack

* **Runtime Environment:** Python 3.13+ packaged as a compiled, single-file native executable via PyInstaller or Nuitka to run without local Python installations.
* **Dependency Management:** `uv` 0.11.21 workspace configuration maintaining separated, lockfile-validated dependency scopes for client and server layers.

---

## 2. Cryptographic Infrastructure & Lifecycle

Security is enforced purely at the transport layer via Mutual TLS (mTLS), backed by an embedded Certificate Authority (CA) inside the server module.

### 2.1 The Bootstrap Provisioning Protocol

Since generic client binaries cannot safely embed global cryptographic identities, enrollment follows a strict initialization flow:

```
[Client Deployment]              [FastAPI Bootstrap Endpoint]            [Embedded CA Module]
        |                                     |                                    |
        |--- 1. POST /enroll (Token + CSR) -->|                                    |
        |                                     |--- 2. Validate Token & CSR ------>|
        |                                     |                                    |
        |                                     |<-- 3. Issue Signed Client Cert ---|
        |<-- 4. Return Signed Certificate ----|                                    |
        |                                     |                                    |

```

1. **Token Generation:** An administrator creates a high-entropy, short-lived (e.g., 24-hour expiration) One-Time Enrollment Token via the server dashboard.
2. **Key Generation & CSR Creation:** The client installer executes with the token as an execution flag. The agent immediately generates an asymmetric private key pair locally and packages its system details into a Certificate Signing Request (CSR).
3. **The Bootstrap Request:** The client performs a standard HTTPS POST request containing the enrollment token and the raw CSR payload to `/api/v1/enroll`.
4. **Verification & Signing:** The server validates the token against SQLite, verifies the incoming CSR signature, records the machine profile, and passes the public key to the internal CA engine. The CA signs a new client certificate.
5. **Hardening and Locking:** The server returns the signed certificate payload to the client. The client saves the certificate file to disk and programmatically triggers operating system filesystem locks:
* **Linux:** Executes a strict `chmod 600` permission mask over the private key directory.
* **Windows:** Modifies the security descriptor to enforce access exclusively to the `SYSTEM` and `Administrators` security groups via Access Control Lists (ACLs).


6. **mTLS Lock:** The token is invalidated. The client drops standard HTTP and initiates all future connections strictly over mTLS via port 443.

### 2.2 Combined Revocation and Short-Lived Lifecycle

* **Short-Lived Cert Lifespans:** To minimize exposure if an agent machine is physically compromised, client certificates are issued with restrictive expiration terms (e.g., 7 days). The client background daemon initiates an asynchronous renewal sequence automatically when reaching 80% of certificate life.
* **Certificate Revocation List (CRL):** If an administrator explicitly deletes or flag-marks a client node via the monitoring workspace, its certificate serial number and unique cryptographic fingerprint are written into the SQLite `certificates_crl` table. The FastAPI mTLS validation layer checks this table on every incoming socket connection, severing active TCP links instantly upon revocation.

---

## 3. Media Pipeline & Stream Escalation Logic

To maintain high performance without overloading the network or server hardware, streaming scales dynamically across two operational tires.

```
                                  +-----------------------+
                                  | Client Daemon Started |
                                  +-----------------------+
                                              |
                                              v
                                 +-------------------------+
                                 | Established mTLS WS     |
                                 | Connection to Server    |
                                 +-------------------------+
                                              |
                                              v
                                 +-------------------------+
                                 |  [TIER 1] THUMBNAIL     |
                                 |  Pushes low-res frame   |
                                 |  every 3 seconds via WS |
                                 +-------------------------+
                                              |
                     ===================================================
                     |                                                 |
         [Admin Clicks Node Grid]                          [Admin Closes Focus View]
                     |                                                 |
                     v                                                 v
        +-------------------------+                       +-------------------------+
        | Receive START_WEBRTC    |                       | Receive STOP_WEBRTC     |
        | Signaled from Server    |                       | Signaled from Server    |
        +-------------------------+                       +-------------------------+
                     |                                                 |
                     v                                                 |
        +-------------------------+                                    |
        |  [TIER 2] FOCUS MODE    |                                    |
        |  Negotiates SDP/ICE.    |                                    |
        |  Spins up hardware      |                                    |
        |  H.264 WebRTC Stream    |------------------------------------+
        +-------------------------+

```

### 3.1 Tier 1: Thumbnail Streaming (Default Idle State)

* **Mechanism:** While a node resides inside the standard un-focused dashboard viewport, the client capture engine bypasses heavy video encodings. It takes a compressed screenshot, downscales it to low resolutions, and pushes the binary payload as an asynchronous message directly over the established mTLS WebSocket connection every 3 seconds.
* **Server Handling:** The FastAPI server forwards this thumbnail binary straight to the matching interface container on the client frontend without decompression or modification.

### 3.2 Tier 2: Focus Mode (WebRTC Escalation)

* **Trigger Event:** An administrator clicks an individual monitor thumbnail in the Tailwind v4 grid layout.
* **Signaling Channel Negotiation:** The server issues a structural JSON instruction (`START_WEBRTC`) over the active WebSocket connection. The client and server initiate an asynchronous Session Description Protocol (SDP) offer/answer exchange, alongside Interactive Connectivity Establishment (ICE) candidate gathering.
* **Hardware Acceleration Execution:** Once the WebRTC peer-to-peer connection resolves, the client daemon activates its hardware-accelerated video streaming thread, tapping directly into native OS screen encoders (e.g., NVENC, Intel QuickSync, or Apple Toolbox) to compress live frames into a real-time H.264 video feed.
* **Teardown Protocol:** When the admin closes the focused modal window, the server transmits a `STOP_WEBRTC` command over the signaling channel. The client destroys the WebRTC media pipeline loop and falls back cleanly into the lightweight Thumbnail Mode loop.

---

## 4. Dual-Tier Telemetry Architecture

The client error diagnostic engine utilizes an isolated tracking thread operating with strict split-routing priorities to maintain total system visibility under network or infrastructure failures.

```
       +-------------------------------------------------------+
       |             Client Operational Exception              |
       +-------------------------------------------------------+
                                   |
                     +-------------+-------------+
                     |                           |
        [Local Parent Server Up]     [Local Parent Server Down]
                     |                           |
                     v                           v
       +---------------------------+ +---------------------------+
       | Primary Route:            | | Fallback Route:           |
       | POST to Local Parent URL  | | POST to Global Remote     |
       | /api/v1/telemetry         | | Developer Telemetry Hook  |
       +---------------------------+ +---------------------------+

```

* **Primary Loop Transmission:** The client records application alerts, operating metrics, and non-fatal tracebacks into an internal, asynchronous memory queue. Under normal conditions, these are posted in batches to the local server space at `/api/v1/telemetry`.
* **Out-of-Band Redirect Engine:** The telemetry module operates independently from the main WebSocket thread. If a connection exception indicates that the local parent server is unreachable, or if an unhandled runtime crash threatens to kill the main daemon execution loop, the client bypasses its standard connection configurations. It targets a globally hardcoded, 24/7-operational Developer Telemetry Hook external to the local company network. This ensures diagnostic payloads are preserved even during local infrastructure failures.

---

## 5. Database Schema & API Specifications

### 5.1 SQLite Relational Schema

The database layer uses an embedded SQLite architecture designed for high read/write speeds over localized connection scopes.

#### Table: `users`

| Column Name     | Data Type | Constraints                | Description                                                  |
| --------------- | --------- | -------------------------- | ------------------------------------------------------------ |
| `id`            | INTEGER   | PRIMARY KEY, AUTOINCREMENT | System identifier for web dashboard administrators.          |
| `username`      | TEXT      | UNIQUE, NOT NULL           | Unique login credential identity.                            |
| `password_hash` | TEXT      | NOT NULL                   | Argon2 or bcrypt cryptographic password verification string. |
| `role`          | TEXT      | NOT NULL                   | System permissions tier (e.g., `SuperAdmin`, `Viewer`).      |

#### Table: `monitors`

| Column Name   | Data Type | Constraints                | Description                                                       |
| ------------- | --------- | -------------------------- | ----------------------------------------------------------------- |
| `id`          | INTEGER   | PRIMARY KEY, AUTOINCREMENT | System identifier for target client units.                        |
| `common_name` | TEXT      | UNIQUE, NOT NULL           | Cryptographic certificate name value matching client hardware ID. |
| `hostname`    | TEXT      | NOT NULL                   | Operating system network hostname string.                         |
| `status`      | TEXT      | NOT NULL                   | Real-time state flags (e.g., `Online`, `Offline`, `Streaming`).   |
| `last_seen`   | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP  | Tracks the last valid cryptographic heartbeat received.           |

#### Table: `certificates_crl`

| Column Name   | Data Type | Constraints                | Description                                                       |
| ------------- | --------- | -------------------------- | ----------------------------------------------------------------- |
| `id`          | INTEGER   | PRIMARY KEY, AUTOINCREMENT | Revocation tracking list identifier.                              |
| `fingerprint` | TEXT      | UNIQUE, NOT NULL           | Cryptographic SHA-256 string hash of the revoked client cert.     |
| `revoked_at`  | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP  | Server-side record of when connectivity authorization was pulled. |

---

### 5.2 API & Endpoint Mapping

| HTTP Method / Protocol | Endpoint Path        | Authentication       | Description                                                                                                |
| ---------------------- | -------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------- |
| **POST**               | `/api/v1/enroll`     | Bootstrap Token      | Un-authenticated TLS bootstrap endpoint to exchange client CSR for an operational signed mTLS certificate. |
| **GET**                | `/api/v1/auth/login` | None                 | Renders the initial Tailwind v4 admin credential entry viewport.                                           |
| **POST**               | `/api/v1/auth/login` | Form Data            | Validates admin user credentials and issues temporary HTTP-only cookies.                                   |
| **GET**                | `/dashboard`         | Cookie Session       | Compiles and injects the live paginated 4x2 or 5x2 thumbnail view grid.                                    |
| **POST**               | `/api/v1/telemetry`  | mTLS Cert Validation | Target ingest for client performance data and structural operational logs under standard states.           |
| **WS**                 | `/ws/signaling`      | mTLS Cert Validation | Persistent bidirectional pipeline handling low-latency idle thumbnails and WebRTC signaling tokens.        |

---

---

# PRODUCTION ARCHITECTURE CODESPACE DIAGRAM

```text
sensiwatch/
├── pyproject.toml                  # Root uv workspace configuration
├── uv.lock                         # Monorepo-wide unified lockfile
├── README.md                       # High-level architecture documentation
│
├── server/                         # FastAPI Server Space
│   ├── pyproject.toml              # Server-specific dependencies
│   ├── Dockerfile                  # Server containerization recipe
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # FastAPI application initialization
│       ├── core/                   # System-wide configuration and core engines
│       │   ├── config.py           # Environment variables & system constants
│       │   ├── database.py         # SQLite connection & database initialization
│       │   └── security/           # Cryptographic & mTLS validation layer
│       │       ├── ca_engine.py    # Embedded CA (Cert signing & verification)
│       │       └── crl_manager.py  # SQLite-backed Certificate Revocation List
│       │
│       ├── database/               # Data Layer
│       │   ├── models.py           # SQLite relational schemas (monitors, users, crl)
│       │   └── crud.py             # Database access operations
│       │
│       ├── api/                    # REST API Endpoints
│       │   ├── v1/
│       │   │   ├── auth.py         # Admin authentication & session management
│       │   │   ├── enroll.py       # One-time bootstrap token & CSR verification
│       │   │   └── telemetry.py    # Primary log ingestion & diagnostics hook
│       │
│       ├── services/               # Background Services & Real-time Engines
│       │   ├── signaling.py        # Asynchronous WebSocket signaling manager
│       │   └── stream_manager.py   # WebRTC session negotiation controller
│       │
│       └── ui/                     # Admin Dashboard Frontend (Tailwind v4)
│           ├── templates/
│           │   ├── base.html       # Shared structural layout
│           │   ├── login.html      # Secure admin authentication page
│           │   └── dashboard.html  # Responsive 4x2 / 5x2 paginated monitoring grid
│           └── static/
│               ├── css/            # Tailwind v4 output stylesheet
│               └── js/             # WebRTC signaling, Toastify alerts, Lucide icons
│
├── client/                         # Headless Background Agent
│   ├── pyproject.toml              # Client-specific minimal dependencies
│   └── src/
│       ├── __init__.py
│       ├── daemon.py               # Main background service entry point & state machine
│       ├── core/                   # Security & configuration storage
│       │   ├── config.py           # Target server URLs & hardcoded developer hooks
│       │   └── storage.py          # OS-level path handling & certificate ACL hardening
│       │
│       ├── capture/                # Video Pipeline Engine
│       │   ├── grabber.py          # Low-overhead screen frame grabber
│       │   └── encoder.py          # Hardware-accelerated video compression engine
│       │
│       └── network/                # Network Transport Layer
│           ├── bootstrap.py        # One-time enrollment execution & key generation
│           ├── connection.py       # Persistent mTLS WebSocket connection client
│           ├── webrtc_agent.py     # Client-side WebRTC peer connection handler
│           └── telemetry.py        # Out-of-band fault detection and redirector
│
├── shared/                         # Common Protocols & Configuration Schemas
│   ├── __init__.py
│   └── constants.py                # Common messaging schemas, codes, and protocols
│
└── deploy/                         # Enterprise Infrastructure Deployment
    ├── docker-compose.yml          # On-premise server deployment setup
    └── installers/
        ├── windows/                # Configuration for generating silent MSI/NSIS installers
        └── linux/                  # Configuration for systemd service and DEB packaging

```