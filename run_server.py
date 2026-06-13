import asyncio
import sys
from pathlib import Path

# Add root dir to sys path to ensure clean imports
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

import uvicorn
from server.app.main import app


async def main() -> None:
    # 1. Config for Port 8000 (Standard HTTPS for Chrome and Bootstrap API)
    config_8000 = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8000,
        ssl_keyfile="ca_storage/ca_key.pem",
        ssl_certfile="ca_storage/ca_cert.pem",
        log_level="info",
    )

    # 2. Config for Port 8443 (Strict mTLS for Client Daemon WebSocket) [3]
    config_8443 = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8443,
        ssl_keyfile="ca_storage/ca_key.pem",
        ssl_certfile="ca_storage/ca_cert.pem",
        ssl_ca_certs="ca_storage/ca_cert.pem",
        ssl_cert_reqs=2,  # Enforces client certificate verification strictly [3]
        log_level="info",
    )

    server_8000 = uvicorn.Server(config_8000)
    server_8443 = uvicorn.Server(config_8443)

    print("\n" + "="*60)
    print(" SENSIWATCH UNIFIED DUAL-PORT RUNNER ACTIVE")
    print(" - Admin Web UI: https://127.0.0.1:8000")
    print(" - Secure mTLS Portal: https://127.0.0.1:8443")
    print("="*60 + "\n")

    # Run both servers concurrently in the same memory loop!
    await asyncio.gather(
        server_8000.serve(),
        server_8443.serve()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] SensiWatch runner stopped cleanly.")