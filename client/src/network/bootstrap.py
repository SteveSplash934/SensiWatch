import logging
import socket
from pathlib import Path
import httpx

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID

from client.src.core.storage import get_cert_dir, secure_file_permissions

logger = logging.getLogger(__name__)


async def run_bootstrap(token: str, server_url: str) -> bool:
    """
    Executes the one-time bootstrap provisioning protocol.
    Generates local keys, creates a CSR, fetches the mTLS certificate from the server,
    and secures all local cryptographic files.
    """
    cert_dir = get_cert_dir()
    key_path = cert_dir / "client_key.pem"
    cert_path = cert_dir / "client_cert.pem"

    # Short circuit if already enrolled
    if key_path.exists() and cert_path.exists():
        logger.info("Local keys and certificates already present. Skipping bootstrap.")
        return True

    try:
        # 1. Generate Local Private Key (ECDSA SECP256R1)
        logger.info("Generating asymmetric local private key...")
        private_key = ec.generate_private_key(ec.SECP256R1())

        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Apply strict ACL lock immediately on the key
        secure_file_permissions(key_path)

        # 2. Generate Certificate Signing Request (CSR)
        logger.info("Assembling Certificate Signing Request (CSR)...")
        hostname = socket.gethostname()
        
        csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SensiWatch Enterprise Client"),
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ])).sign(private_key, hashes.SHA256())

        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")

        # 3. Post CSR to server bootstrap endpoint
        logger.info(f"Submitting CSR and Token to {server_url}/api/v1/enroll...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{server_url}/api/v1/enroll",
                json={"token": token, "csr": csr_pem},
                headers={"Content-Type": "application/json"},
                timeout=15.0
            )
            
            if response.status_code != 200:
                logger.error(f"Enrollment rejected by server: {response.text}")
                # Clean up insecure key if enrollment failed
                key_path.unlink(missing_ok=True)
                return False

            data = response.json()
            cert_data = data.get("certificate")
            if not cert_data:
                raise ValueError("Server returned an empty certificate response.")

        # 4. Save and Lock Certificate
        logger.info("Saving operational signed certificate...")
        with open(cert_path, "wb") as f:
            f.write(cert_data.encode("utf-8"))

        secure_file_permissions(cert_path)
        logger.info("mTLS Client Enrollment completed successfully and locked.")
        return True

    except Exception as e:
        logger.critical(f"Fatal error during bootstrap enrollment: {e}")
        # Clean up key/cert state on failure to avoid leaving a corrupted partial setup
        key_path.unlink(missing_ok=True)
        cert_path.unlink(missing_ok=True)
        return False