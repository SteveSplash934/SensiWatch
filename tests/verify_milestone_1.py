import asyncio
import datetime
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


async def seed_test_token(token_str: str) -> None:
    """Insert a valid dummy token directly into the SQLite database for testing."""
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
        # Clear any prior validation tokens
        await session.execute(text("DELETE FROM enrollment_tokens"))
        
        token = EnrollmentToken(
            token_value=token_str,
            expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
            is_used=False
        )
        session.add(token)
        await session.commit()
    await engine.dispose()


async def run_validation() -> None:
    db_file = ROOT_DIR / "sensiwatch.db"
    server_process = None

    try:
        # Cleanup previous runs to ensure fresh state
        try:
            db_file.unlink(missing_ok=True)
            shutil.rmtree(ROOT_DIR / "ca_storage", ignore_errors=True)
        except PermissionError:
            print("\n" + "!"*60)
            print("[!] ERROR: sensiwatch.db is currently locked by a lingering process.")
            print("[!] Please run this in your terminal to free it:  taskkill /F /IM python.exe")
            print("!"*60 + "\n")
            return

        test_token = secrets.token_hex(16)
        print(f"[!] Target validation token generated: {test_token}")

        # 1. Seed the database with our validation token (Ensures DB is built before server binds)
        print("[*] Pre-seeding database and validation token in SQLite...")
        await seed_test_token(test_token)

        # 2. Start FastAPI server as a background subprocess (using sys.executable directly to avoid orphaning)
        print("[*] Launching server on http://127.0.0.1:8000...")
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=None,
            stderr=None,
            cwd=str(ROOT_DIR)
        )
        
        # Wait for server spin up
        time.sleep(3)

        # 3. Execute client-side bootstrap
        print("[*] Triggering client-side bootstrap sequence...")
        from client.src.network.bootstrap import run_bootstrap
        
        success = await run_bootstrap(test_token, "http://127.0.0.1:8000")
        
        if success:
            print("\n" + "="*50)
            print(" VALIDATION SUCCESSFUL!")
            print("="*50)
            from client.src.core.storage import get_cert_dir
            cert_dir = get_cert_dir()
            print(f"Key saved to:  {cert_dir / 'client_key.pem'}")
            print(f"Cert saved to: {cert_dir / 'client_cert.pem'}")
            print("="*50)
        else:
            print("\n" + "!"*50)
            print(" VALIDATION FAILED: Client failed to enroll.")
            print("!"*50)

    finally:
        if server_process is not None:
            print("[*] Shutting down background server...")
            server_process.terminate()
            server_process.wait()


if __name__ == "__main__":
    asyncio.run(run_validation())