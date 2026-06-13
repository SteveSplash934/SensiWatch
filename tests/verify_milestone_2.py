import asyncio
import datetime
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Resolve monorepo root dynamically
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


async def seed_test_token(token_str: str) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from server.app.database.models import EnrollmentToken
    from server.app.core.database import Base
    
    db_path = ROOT_DIR / "sensiwatch.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        from sqlalchemy import text
        await session.execute(text("DELETE FROM enrollment_tokens"))
        await session.execute(text("DELETE FROM monitors"))
        
        token = EnrollmentToken(
            token_value=token_str,
            expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
            is_used=False
        )
        session.add(token)
        await session.commit()
    await engine.dispose()


async def check_monitor_status() -> tuple[str, str]:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from server.app.database.models import Monitor
    from sqlalchemy import select

    db_path = ROOT_DIR / "sensiwatch.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async_session = async_sessionmaker(engine)

    async with async_session() as session:
        query = select(Monitor)
        result = await session.execute(query)
        monitor = result.scalar_one_or_none()
        if monitor:
            return monitor.common_name, monitor.status
        return "None", "None"


async def run_validation() -> None:
    db_file = ROOT_DIR / "sensiwatch.db"
    server_process = None
    client_process = None

    try:
        # Cleanup
        try:
            db_file.unlink(missing_ok=True)
            shutil.rmtree(ROOT_DIR / "ca_storage", ignore_errors=True)
            # Remove client certificates to force fresh bootstrap enrollment
            from client.src.core.storage import get_cert_dir
            shutil.rmtree(get_cert_dir(), ignore_errors=True)
        except PermissionError:
            print("[!] ERROR: sensiwatch.db is locked. Run: taskkill /F /IM python.exe")
            return

        test_token = secrets.token_hex(16)
        
        # 1. Generate the Embedded CA certs upfront so Uvicorn can load them on boot
        print("[*] Generating server CA certificates...")
        from server.app.core.security.ca_engine import EmbeddedCA
        _ca = EmbeddedCA(ca_dir=ROOT_DIR / "ca_storage")

        print(f"[*] Pre-seeding database and validation token in SQLite...")
        await seed_test_token(test_token)

        # 2. Start Uvicorn Server with optional mTLS constraints (allowing bootstrap to connect)
        print("[*] Launching mTLS server on https://127.0.0.1:8000...")
        server_process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "server.app.main:app", 
                "--host", "127.0.0.1", "--port", "8000",
                "--ssl-keyfile", str(ROOT_DIR / "ca_storage" / "ca_key.pem"),
                "--ssl-certfile", str(ROOT_DIR / "ca_storage" / "ca_cert.pem"),
                "--ssl-ca-certs", str(ROOT_DIR / "ca_storage" / "ca_cert.pem"),
                "--ssl-cert-reqs", "1"  # Optional client verification (enforced in code for /ws/signaling) [3]
            ],
            stdout=None,
            stderr=None,
            cwd=str(ROOT_DIR)
        )
        time.sleep(3)

        # 3. Start Client Daemon in the background (pointing to secure HTTPS and WSS endpoints)
        print("[*] Launching Client Daemon in the background...")
        client_process = subprocess.Popen(
            [
                sys.executable, "-m", "client.src.daemon", 
                "--server", "https://127.0.0.1:8000", 
                "--ws", "wss://127.0.0.1:8000/ws/signaling", 
                "--token", test_token
            ],
            stdout=None,
            stderr=None,
            cwd=str(ROOT_DIR)
        )
        
        # Give enough time for client to bootstrap AND then connect via secure WebSocket
        time.sleep(6)

        # 4. Read SQLite state (Verify Client is registered as ONLINE)
        cn, status = await check_monitor_status()
        print(f"[*] Querying database: Monitor [{cn}] status is [{status}]")

        if status != "Online":
            print("[!] Validation failed: Client was not registered as Online in SQLite.")
            return

        # 5. Terminate Client Daemon
        print("[*] Terminating Client Daemon to simulate disconnection...")
        client_process.terminate()
        client_process.wait()
        client_process = None
        
        # Wait for disconnect ASGI trigger to finish database write
        time.sleep(2)

        # 6. Read SQLite state again (Verify Client has transitioned to OFFLINE)
        cn, status = await check_monitor_status()
        print(f"[*] Querying database: Monitor [{cn}] status is [{status}]")

        if status == "Offline":
            print("\n" + "="*50)
            print(" MILESTONE 2 VALIDATION SUCCESSFUL!")
            print(" Presence and Heartbeat tracking is fully green.")
            print("="*50 + "\n")
        else:
            print("[!] Validation failed: Status did not transition to Offline.")

    finally:
        if client_process is not None:
            client_process.terminate()
            client_process.wait()
        if server_process is not None:
            server_process.terminate()
            server_process.wait()


if __name__ == "__main__":
    asyncio.run(run_validation())