import os
import platform
import subprocess
from pathlib import Path


def get_app_dir() -> Path:
    """Retrieve the platform-specific root application directory."""
    if platform.system() == "Windows":
        # System-wide program data directory for headless agents
        base = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
        app_dir = Path(base) / "SensiWatch"
    else:
        # Standard system daemon variable data folder on Unix-likes
        app_dir = Path("/var/lib/sensiwatch")
        
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fallback to local user home directory if executing unprivileged
        app_dir = Path.home() / ".sensiwatch"
        app_dir.mkdir(parents=True, exist_ok=True)

    return app_dir


def get_cert_dir() -> Path:
    """Retrieve the subdirectory designated for cryptographic assets."""
    cert_dir = get_app_dir() / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    return cert_dir


def secure_file_permissions(filepath: Path) -> None:
    """Enforce strict ACLs on sensitive cryptographic material based on host OS."""
    if not filepath.exists():
        return

    if platform.system() == "Windows":
        # Lock inheritance and permit access ONLY to SYSTEM and Administrators
        subprocess.run([
            "icacls", str(filepath),
            "/inheritance:r",
            "/grant:r", "SYSTEM:F",
            "/grant:r", "Administrators:F"
        ], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # Strict POSIX: Read/Write by owner (chmod 600)
        os.chmod(filepath, 0o600)